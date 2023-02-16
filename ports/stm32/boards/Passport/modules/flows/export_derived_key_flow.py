# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# export_derived_key_flow.py - Export a derived key

from flows import Flow


class ExportDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        self.key = context
        self.format = None
        self.num_words = None
        self.pk = None
        super().__init__(initial_state=self.choose_key_format, name="NewDerivedKeyFlow")

    async def choose_key_format(self):
        from pages import ChooserPage
        from derived_key import key_types

        options = []
        if key_types[self.key['type']]['words']:
            options = [{'label': '24 words', 'value': '24'},
                       {'label': '12 words', 'value': '12'}]
        else:
            options = [{'label': 'Private Key', 'value': 'key'}]

        self.format = await ChooserPage(card_header={'title': 'Key Format'}, options=options).show()

        if self.format is None:
            self.set_result(False)
            return

        if self.format.isdigit():
            self.num_words = int(self.format)
        else:
            self.num_words = 0

        self.goto(self.generate_key)

    async def generate_key(self):
        from utils import spinner_task
        from derived_key import key_types
        from pages import ErrorPage

        (self.pk, error) = await spinner_task(text='Generating Key',
                                              task=key_types[self.key['type']]['task'],
                                              args=[self.num_words, self.key['index']])
        if error is not None:
            await ErrorPage(error).show()
            self.set_result(False)
            return

        self.goto(self.choose_export_mode)

    async def choose_export_mode(self):
        from pages import ChooserPage
        from derived_key import key_types

        options = [{'label': 'Export via QR', 'value': self.show_qr_code},
                   {'label': 'Export via SD', 'value': self.save_to_sd}]

        if key_types[self.key['type']]['words']:
            options.append({'label': 'Show seed words', 'value': self.show_seed_words})

        mode = await ChooserPage(card_header={'title': 'Export Mode'}, options=options).show()

        if mode is None:
            self.set_result(False)
            return

        self.goto(mode)

    async def show_qr_code(self):
        from pages import ShowQRPage
        from utils import B2A
        import microns
        await ShowQRPage(qr_data=B2A(self.pk), right_micron=microns.Checkmark).show()
        self.set_result(True)

    async def save_to_sd(self):
        from files import CardSlot, CardMissingError
        from pages import ErrorPage
        from utils import file_exists
        from utils import B2A
        from derived_key import key_types

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
                                                 key_types[self.key['type']]['title'],
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
        result = await InsertMicroSDPage().show()
        if not result:
            self.set_result(False)
        else:
            self.goto(self.create_file)

    async def show_success(self):
        from pages import SuccessPage
        await SuccessPage(text='Saved key as {}.'.format(self.file_path)).show()
        self.set_result(True)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow(external_key=self.pk).run()
        self.goto(self.show_qr_code)
        self.set_result(True)
