# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_derived_key_flow.py - Export a derived key

from flows import Flow


class ExportDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        self.key = context
        self.key_type = None
        self.pk = None
        super().__init__(initial_state=self.generate_key, name="NewDerivedKeyFlow")

    async def generate_key(self):
        from utils import spinner_task
        from derived_key import get_key_type_from_tn
        from pages import ErrorPage

        self.key_type = get_key_type_from_tn(self.key['tn'])

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        (self.pk, error) = await spinner_task(text='Generating Key',
                                              task=self.key_type['task'],
                                              args=[self.key['index']])
        if error is not None:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        self.goto(self.choose_export_mode)

    async def choose_export_mode(self):
        from pages import ChooserPage

        options = [{'label': 'Export via QR', 'value': self.show_qr_code},
                   {'label': 'Export via microSD', 'value': self.save_to_sd}]

        if self.key_type['words']:
            options.append({'label': 'Show seed words', 'value': self.show_seed_words})

        mode = await ChooserPage(card_header={'title': 'Export Mode'}, options=options).show()

        if mode is None:
            self.set_result(False)
            return

        self.goto(mode)

    async def show_qr_code(self):
        from flows import GetSeedWordsFlow
        from pages import ShowQRPage, ChooserPage
        from utils import B2A
        from data_codecs.qr_type import QRType
        import microns

        if self.key_type['words']:
            options = [{'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                       {'label': 'SeedQr', 'value': QRType.SEED_QR}]

            qr_type = await ChooserPage(card_header={'title': 'QR Format'}, options=options).show()
        else:
            qr_type = QRType.QR

        if qr_type is None:
            self.set_result(False)
            return

        if qr_type is QRType.QR:
            if isinstance(self.pk, str):
                qr_data = self.pk
            else:
                qr_data = B2A(self.pk)
        else:  # SeedQR or Compact SeedQR
            qr_data = await GetSeedWordsFlow(self.pk).run()

            if qr_data is None:
                self.set_result(False)
                return

        await ShowQRPage(qr_type=qr_type, qr_data=qr_data, right_micron=microns.Checkmark).show()
        self.set_result(True)

    async def save_to_sd(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage
        from utils import file_exists
        from utils import B2A
        from flows import GetSeedWordsFlow

        if self.key_type['words']:
            words = await GetSeedWordsFlow(self.pk).run()
            text = " ".join(words)
        elif isinstance(self.pk, str):
            text = self.pk
        else:
            text = B2A(self.pk)

        key_num = 1

        while True:
            try:
                with CardSlot() as card:
                    path = card.get_sd_root()
                    # Make a unique filename
                    while True:
                        self.file_path = '{}/{}-{}-{}.txt' \
                                         .format(path,
                                                 self.key_type['title'],
                                                 self.key['name'],
                                                 key_num)
                        self.file_path = self.file_path.replace(' ', '_')
                        # Ensure filename doesn't already exist
                        if not file_exists(self.file_path):
                            break

                        # Ooops...that exists, so increment and try again
                        key_num += 1

                    # Do actual write
                    with open(self.file_path, 'w') as fd:
                        fd.write(text)
                self.goto(self.show_success)
                return

            except CardMissingError:
                self.goto(self.show_insert_microsd_error)
                return
            except Exception as e:
                self.error = e.args[0]
                await ErrorPage(text=self.error).show()
                self.set_result(False)
                return

    async def show_insert_microsd_error(self):
        from pages import InsertMicroSDPage

        result = await InsertMicroSDPage().show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.save_to_sd)

    async def show_success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved key as {}.'.format(self.file_path)).show()
        self.set_result(True)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(external_key=self.pk).run()
        self.goto(self.show_qr_code)
        self.set_result(True)
