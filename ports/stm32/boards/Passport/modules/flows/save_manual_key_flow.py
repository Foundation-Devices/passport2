# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# save_manual_key_flow.py - Save an external key manually

from flows import Flow


class SaveManualKeyFlow(Flow):
    def __init__(self, context=None, key_type=None):
        self.index = context['index']  # Manual key index
        self.key_type = key_type  # Key type dict
        self.file_path = None

        super().__init__(initial_state=self.input, name="SaveManualKeyFlow")

    def copy_seed(self, seed):
        self.key = seed

    async def input(self):
        from derived_key import get_key_type_from_tn
        from pages import ErrorPage
        from flows import RestoreSeedFlow

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        if self.key_type['words']:
            result = await RestoreSeedFlow(save_seed=False, copy_callback=self.copy_seed).run()
            if not result:
                self.set_result(False)
                return

            self.goto(self.save_key)
            return

        self.goto(choose_import_mode)

    async def choose_import_mode(self):
        from pages import ChooserPage

        options = [{'label': 'Import via QR', 'value': self.scan_qr_code},
                   {'label': 'Import via microSD', 'value': self.choose_file}]

        mode = await ChooserPage(card_header={'title': 'Format'}, options=options).show()

        if mode is None:
            self.set_result(False)
            return

        self.goto(mode)

    async def scan_qr_code(self):
        from flows import ScanQRFlow
        from pages import ErrorPage

        result = await ScanQRFlow(data_description=self.key_type['title']).run()

        if result is None:
            await ErrorPage("Invalid {} detected. Make sure you're using the right format."
                            .format(self.key_type['title'])).show()
            self.back()
            return

        self.key = result

        self.goto(self.save_key)

    async def choose_file(self):
        from flows import FilePickerFlow
        from pages import ErrorPage

        result = await FilePickerFlow(show_folders=True).run()

        if result is None:
            await ErrorPage("Invalid file").show()
            self.back()
            return

        _filename, full_path, is_folder = result
        if not is_folder:
            self.file_path = full_path
            self.goto(self.copy_from_sd)

        # Drop through to file picker again if all else fails

    async def copy_from_sd(self):
        from flows import ReadFileFlow

        data = await ReadFileFlow(self.file_path, binary=False).run()

        if not data:
            self.back()
            return

        self.key = data

        self.goto(self.save_key)

    async def save_key(self):
        from utils import spinner_task
        from tasks import save_new_manual_key_task
        from errors import Error
        from pages import SuccessPage, ErrorPage

        print("key: {}".format(self.key))

        (error,) = await spinner_task('Saving Manual Key',
                                      save_new_manual_key_task,
                                      args=[self.index,
                                            self.key_type['tn'],
                                            self.key])

        print("error: {}".format(error))

        if error is None:
            from flows import AutoBackupFlow

            await SuccessPage(text='Manual key saved.').show()
            await AutoBackupFlow().run()
            self.set_result(True)
            return

        error_msg = 'Manual key failed to save.'

        if error is Error.INDEX_TAKEN_ERROR:
            error_msg = 'Manual key index {} is already taken.'.format(self.index)

        await ErrorPage(error_msg).show()
        self.set_result(False)
