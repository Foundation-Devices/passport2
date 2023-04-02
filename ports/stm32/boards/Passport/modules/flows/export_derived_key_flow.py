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
        from utils import B2A
        from flows import GetSeedWordsFlow
        from flows import SaveToMicroSDFlow

        if self.key_type['words']:
            words = await GetSeedWordsFlow(self.pk).run()
            text = " ".join(words)
        elif isinstance(self.pk, str):
            text = self.pk
        else:
            text = B2A(self.pk)

        filename = '{}-{}.txt'.format(self.key_type['title'], self.key['name'])
        result = await SaveToMicroSDFlow(filename=filename,
                                         data=text,
                                         success_text="key").run()
        self.set_result(result)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(external_key=self.pk).run()
        self.goto(self.show_qr_code)
        self.set_result(True)
