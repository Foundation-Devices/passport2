# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# sign_psbt_microsd_flow.py - Sign a PSBT from a microSD card

from flows import Flow
from pages import InsertMicroSDPage, QuestionPage, LongTextPage


def is_psbt(filename):
    from files import CardSlot

    # print('filenmame={}'.format(filename))
    if '-signed' in filename.lower():
        return False

    sd_root = CardSlot.get_sd_root()
    with open('{}/{}'.format(sd_root, filename), 'rb') as fd:
        taste = fd.read(10)
        # print('taste={}'.format(taste))
        if taste[0:5] == b'psbt\xff':
            return True
        if taste[0:10] == b'70736274ff':        # hex-encoded
            return True
        if taste[0:6] == b'cHNidP':             # base64-encoded
            return True
        return False


class SignPsbtMicroSDFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file, name='SignPsbtMicroSDFlow')

    async def choose_file(self):
        from flows import FilePickerFlow
        from files import CardSlot

        root_path = CardSlot.get_sd_root()

        result = await FilePickerFlow(
            initial_path=root_path, show_folders=True, suffix='psbt', filter_fn=is_psbt).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.copy_file_to_flash)

    async def copy_file_to_flash(self):
        import gc
        from utils import spinner_task
        from pages import ErrorPage
        from public_constants import TXN_INPUT_OFFSET
        from tasks import copy_psbt_file_to_external_flash_task
        from utils import clear_psbt_flash
        from errors import Error

        # TODO: I think this is always a bytes object -- can probably remove this check
        # The data can be a string or may already be a bytes object
        # if isinstance(self.raw_psbt, bytes):
        #     data_buf = self.raw_psbt
        # else:
        #     data_buf = bytes(self.raw_psbt, 'utf-8')

        gc.collect()  # Try to avoid excessive fragmentation

        # TODO: Pass on_progress function as the first argument if we want progress or remove it
        (self.psbt_len, self.output_encoder, error) = await spinner_task(
            'Parsing transaction',
            copy_psbt_file_to_external_flash_task,
            args=[None, self.file_path, TXN_INPUT_OFFSET])
        if error is not None:
            await clear_psbt_flash()
            if error == Error.PSBT_TOO_LARGE:
                await ErrorPage(text='PSBT too large').show()
            else:
                await ErrorPage(text='Invalid PSBT (copying microSD)').show()
            self.set_result(False)
            return

        gc.collect()  # Try to avoid excessive fragmentation

        # PSBT was copied to external flash
        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import SignPsbtCommonFlow
        from utils import clear_psbt_flash

        # This flow validates and signs if all goes well, and returns the signed psbt
        result = await SignPsbtCommonFlow(self.psbt_len).run()
        if result is None:
            await clear_psbt_flash()
            self.set_result(False)
        else:
            self.psbt = result
            self.goto(self.write_signed_transaction)

    async def show_card_missing(self):
        from utils import clear_psbt_flash

        result = await InsertMicroSDPage().show()
        if not result:
            result = QuestionPage(text='Cancel signing this transaction?').show()
            if result:
                await clear_psbt_flash()
                self.set_result(None)

        self.goto(self.write_signed_transaction)

    async def write_signed_transaction(self):
        from files import CardSlot, CardMissingError, securely_blank_file
        from utils import HexWriter
        from pages import ErrorPage
        from utils import clear_psbt_flash

        orig_path, basename = self.file_path.rsplit('/', 1)
        orig_path += '/'
        base = basename.rsplit('.', 1)[0]
        self.out2_fn = None
        self.out_fn = None

        # Try to put back into same spot, but also do top-of-card
        is_comp = self.psbt.is_complete()
        if not is_comp:
            # Keep the filename under control during multiple passes
            target_fname = base.replace('-part', '') + '-part.psbt'
        else:
            # Add -signed to end. We won't offer to sign again.
            target_fname = base + '-signed.psbt'

        for path in [orig_path, None]:
            try:
                with CardSlot() as card:
                    out_full, self.out_fn = card.pick_filename(
                        target_fname, path)
                    out_path = path
                    if out_full:
                        break
            except CardMissingError:
                self.goto(self.show_card_missing)
                return

        if not self.out_fn:
            self.goto(self.show_card_missing)
            return
        else:
            # Attempt to write-out the transaction
            try:
                with CardSlot() as card:
                    with self.output_encoder(open(out_full, 'wb')) as fd:
                        # save as updated PSBT
                        self.psbt.serialize(fd)

                    if is_comp:
                        # write out as hex too, if it's final
                        out2_full, self.out2_fn = card.pick_filename(base + '-final.txn', out_path)
                        if out2_full:
                            with HexWriter(open(out2_full, 'w+t')) as fd:
                                # save transaction, in hex
                                self.txid = self.psbt.finalize(fd)

                    securely_blank_file(self.file_path)
                    await clear_psbt_flash()

                # Success and done!
                self.goto(self.show_success)
                return

            except OSError as exc:
                # If this ever changes to not fall through, clear the flash
                # await clear_psbt_flash()
                result = await ErrorPage(text='Unable to write!\n\n%s\n\n' % exc).show()
                # sys.print_exception(exc)
                # fall thru to try again

    async def show_success(self):
        import microns
        from lvgl import LARGE_ICON_SUCCESS
        from styles.colors import DEFAULT_LARGE_ICON_COLOR
        msg = "Updated PSBT is:\n\n%s" % self.out_fn
        if self.out2_fn:
            msg += '\n\nFinalized transaction (ready for broadcast):\n\n%s' % self.out2_fn

            if self.txid:
                msg += '\n\nFinal TXID:\n' + self.txid

        await LongTextPage(text=msg, centered=True, left_micron=None,
                           right_micron=microns.Checkmark, icon=LARGE_ICON_SUCCESS,
                           icon_color=DEFAULT_LARGE_ICON_COLOR,).show()
        self.set_result(self.psbt)
