# SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# casa_health_check_flow.py - Scan and process a Casa health check QR code in `crypto-request` format

from flows import Flow


def is_health_check(filename):
    from files import CardSlot

    # print('filenmame={}'.format(filename))
    if '-signed' in filename.lower():
        return False

    if '-hc' in filename.lower():
        return True
    return False


class CasaHealthCheckMicrosdFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_file, name='CasaHealthCheckMicrosdFlow')
        self.file_path = None
        self.lines = None
        self.signed_message = None

    async def choose_file(self):
        from flows import FilePickerFlow
        from files import CardSlot

        root_path = CardSlot.get_sd_root()

        result = await FilePickerFlow(
            initial_path=root_path, show_folders=True, filter_fn=is_health_check).run()
        if result is None:
            self.set_result(False)
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.parse_message)

    async def parse_message(self):
        from files import CardSlot
        from pages import ErrorPage

        with open(self.file_path, 'r') as fd:
            try:
                self.lines = fd.read().split('\n')
            except Exception as e:
                await ErrorPage(text='Health check format is invalid.').show()
                self.set_result(False)
                return
        self.goto(self.common_flow)

    async def common_flow(self):
        from flows import CasaHealthCheckCommonFlow

        self.signed_message = await CasaHealthCheckCommonFlow(self.lines).run()
        if self.signed_message is None:
            self.set_result(False)
            return
        self.goto(self.write_signed_file)

    async def write_signed_file(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage

        orig_path, basename = self.file_path.rsplit('/', 1)
        orig_path += '/'
        base = basename.rsplit('.', 1)[0]
        self.out_fn = None

        # Add -signed to end. We won't offer to sign again.
        target_fname = base + '-signed.txt'

        for path in [orig_path, None]:
            try:
                with CardSlot() as card:
                    out_full, self.out_fn = card.pick_filename(
                        target_fname, path)
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
                with open(out_full, 'w') as fd:
                    fd.write(self.signed_message)
            except OSError as exc:
                result = await ErrorPage(text='Unable to write!\n\n%s\n\n' % exc).show()
                # sys.print_exception(exc)
                # fall thru to try again

            # Success and done!
            self.goto(self.show_success)
            return

    async def show_success(self):
        import microns
        from lvgl import LARGE_ICON_SUCCESS
        from styles.colors import DEFAULT_LARGE_ICON_COLOR
        from pages import LongTextPage
        msg = "Updated Health Check is:\n\n%s" % self.out_fn

        await LongTextPage(text=msg, centered=True, left_micron=None,
                           right_micron=microns.Checkmark, icon=LARGE_ICON_SUCCESS,
                           icon_color=DEFAULT_LARGE_ICON_COLOR,).show()
        self.set_result(True)
