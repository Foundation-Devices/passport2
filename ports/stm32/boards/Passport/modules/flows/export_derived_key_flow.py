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
        self.qr_type = None
        self.words = None
        super().__init__(initial_state=self.generate_key, name="NewDerivedKeyFlow")

    async def generate_key(self):
        from utils import spinner_task
        from derived_key import get_key_type_from_tn
        from pages import ErrorPage
        from flows import GetSeedWordsFlow

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

        if self.key_type['words']:
            self.words = await GetSeedWordsFlow(external_key=self.pk, text='Generating Key').run()

            if self.words is None:
                self.set_result(False)
                return

        self.goto(self.choose_export_mode)

    async def choose_export_mode(self):
        from pages import ChooserPage

        options = [{'label': 'Export via QR', 'value': self.choose_qr_type},
                   {'label': 'Export via microSD', 'value': self.save_to_sd}]

        if self.key_type['words']:
            options.append({'label': 'Show seed words', 'value': self.show_seed_words})

        mode = await ChooserPage(card_header={'title': 'Export Mode'}, options=options).show()

        # TODO: if key_type['words'] and not save_to_sd, use ViewSeedWordsFlow

        if mode is None:
            self.set_result(False)
            return

        self.goto(mode)

    async def choose_qr_type(self):
        from pages import ChooserPage
        from flows import SeedWarningFlow
        from data_codecs.qr_type import QRType

        self.qr_type = QRType.QR

        if self.key_type['words']:
            options = [{'label': 'Compact SeedQR', 'value': QRType.COMPACT_SEED_QR},
                       {'label': 'SeedQR', 'value': QRType.SEED_QR}]

            self.qr_type = await ChooserPage(card_header={'title': 'QR Format'}, options=options).show()

        if self.qr_type is None:
            self.back()
            return

        result = await SeedWarningFlow(action_text="display your {} as a QR code"
                                       .format(self.key_type['title'])).run()
        if not result:
            self.back()
            return

        if self.qr_type in [QRType.SEED_QR, QRType.COMPACT_SEED_QR]:
            self.goto(self.show_seed_qr)
            return

        self.goto(show_qr_code)

    async def show_seed_qr(self):
        from pages import ShowQRPage
        import microns

        result = await ShowQRPage(qr_type=self.qr_type, qr_data=self.words, right_micron=microns.Checkmark).show()

        if not result:
            self.back()
            return

        self.goto(self.confirm_seedqr)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from utils import B2A
        import microns

        if isinstance(self.pk, str):
            qr_data = self.pk
        else:
            qr_data = B2A(self.pk)

        result = await ShowQRPage(qr_type=self.qr_type, qr_data=qr_data, right_micron=microns.Checkmark).show()

        if not result:
            self.back()
            return

        self.set_result(True)

    async def confirm_seedqr(self):
        from pages import InfoPage, SeedWordsListPage
        import microns

        plural_label = 's' if len(self.words) == 24 else ''
        text = 'Confirm the seed words in the following page{}.'.format(plural_label)
        result = await InfoPage(text=text, left_micron=microns.Back).show()

        if not result:
            self.back()
            return

        result = await SeedWordsListPage(words=self.words, left_micron=microns.Back).show()

        if not result:
            return

        self.set_result(True)

    async def save_to_sd(self):
        from utils import B2A
        from flows import SaveToMicroSDFlow, SeedWarningFlow

        if self.key_type['words']:
            text = " ".join(self.words)
        elif isinstance(self.pk, str):
            text = self.pk
        else:
            text = B2A(self.pk)

        result = await SeedWarningFlow(action_text="copy your {} to the microSD card"
                                       .format(self.key_type['title']),
                                       continue_text=self.key_type.get('continue_text', None)).run()

        if not result:
            self.set_result(False)
            return

        filename = '{}-{}.txt'.format(self.key_type['title'], self.key['name'])
        result = await SaveToMicroSDFlow(filename=filename,
                                         data=text,
                                         success_text="key").run()
        self.set_result(result)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(external_key=self.pk).run()
        self.set_result(True)
