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
        self.data = None
        self.path = None
        self.filename = None
        super().__init__(initial_state=self.generate_key, name="NewDerivedKeyFlow")

    async def generate_key(self):
        from utils import spinner_task, B2A, get_folder_path
        from derived_key import get_key_type_from_tn
        from pages import ErrorPage
        from flows import ViewSeedWordsFlow
        from public_constants import DIR_KEY_MNGR

        self.key_type = get_key_type_from_tn(self.key['tn'])

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        (vals, error) = await spinner_task(text='Generating key',
                                           task=self.key_type['task'],
                                           args=[self.key['index']])
        self.pk = vals['priv']
        if error is not None:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        self.path = get_folder_path(DIR_KEY_MNGR)
        self.filename = '{}-{}.txt'.format(self.key_type['title'], self.key['name'])

        if self.key_type['words']:
            result = await ViewSeedWordsFlow(external_key=self.pk,
                                             qr_option=True,
                                             sd_option=True,
                                             path=self.path,
                                             filename=self.filename,
                                             key_manager=True).run()
            self.set_result(result)
            return

        if isinstance(self.pk, str):
            self.data = self.pk
        else:
            self.data = B2A(self.pk)

        self.goto(self.choose_export_mode)

    async def choose_export_mode(self):
        from pages import ChooserPage

        options = [{'label': 'Export via QR', 'value': self.show_qr_code},
                   {'label': 'Export via microSD', 'value': self.save_to_sd}]

        mode = await ChooserPage(card_header={'title': 'Format'}, options=options).show()

        if mode is None:
            self.set_result(False)
            return

        self.goto(mode)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from flows import SeedWarningFlow
        import microns

        result = await SeedWarningFlow(action_text="display your child {} as a QR code"
                                       .format(self.key_type['title']),
                                       key_manager=True).run()

        if not result:
            self.back()
            return

        result = await ShowQRPage(qr_data=self.data, right_micron=microns.Checkmark).show()

        if not result:
            return

        self.goto(self.confirm_qr)

    async def confirm_qr(self):
        from pages import InfoPage, LongTextPage
        import microns
        from utils import stylize_address

        text = 'Confirm the exported {} on the following page'.format(self.key_type['title'])
        result = await InfoPage(text=text, left_micron=microns.Back).show()

        if not result:
            self.back()
            return

        result = await LongTextPage(text="\n" + stylize_address(self.data),
                                    centered=True,
                                    card_header={'title': 'Confirm Key'},
                                    left_micron=microns.Back).show()

        if not result:
            return

        self.set_result(True)

    async def save_to_sd(self):
        from flows import SaveToMicroSDFlow, SeedWarningFlow

        result = await SeedWarningFlow(action_text="copy your child {} to the microSD card"
                                       .format(self.key_type['title']),
                                       key_manager=True).run()

        if not result:
            self.back()
            return

        result = await SaveToMicroSDFlow(filename=self.filename,
                                         path=self.path,
                                         data=self.data,
                                         success_text="key").run()
        self.set_result(result)
