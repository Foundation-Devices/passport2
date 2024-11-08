# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# rename_derived_key_flow.py - Rename a derived key

from flows import Flow


class RenameDerivedKeyFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.enter_name, name='RenameDerivedKeyFlow')
        self.key = context
        self.key_name = None
        self.key_type = None

    async def enter_name(self):
        from constants import MAX_ACCOUNT_NAME_LEN
        from pages import TextInputPage, ErrorPage
        import microns
        from utils import get_derived_key_by_name
        from derived_key import get_key_type_from_tn

        self.key_type = get_key_type_from_tn(self.key['tn'])

        if not self.key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        name = self.key['name']

        result = await TextInputPage(card_header={'title': 'Key Name'},
                                     initial_text=name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Cancel,
                                     right_micron=microns.Checkmark).show()

        if result is not None:
            if len(result) == 0:
                # Just show the page again
                return
            self.key_name = result

            # Check for existing account with this name
            existing_key = get_derived_key_by_name(self.key_name, self.key['tn'], self.key['xfp'])
            if existing_key is not None:
                await ErrorPage('{} ##{} already exists with the name "{}".'
                                .format(self.key_type['title'],
                                        existing_key['index'],
                                        self.key_name)).show()
                return

            self.goto(self.rename_key)
        else:
            self.set_result(False)

    async def rename_key(self):
        from tasks import rename_derived_key_task
        from utils import spinner_task
        from flows import AutoBackupFlow, MenuFlow

        (error,) = await spinner_task('Renaming key', rename_derived_key_task,
                                      args=[self.key, self.key_name])
        if error is None:
            if MenuFlow.latest_menu is not None:
                card_header = MenuFlow.latest_menu.get_prev_card_header()
                if card_header is not None:
                    card_header['title'] = "{} ({})".format(self.key_name, self.key['index'])
                    MenuFlow.latest_menu.update_prev_card_header(card_header)
            await AutoBackupFlow().run()
            self.set_result(True)
        else:
            self.error = 'Key NOT renamed: {}'.format(error)
            self.goto(self.show_error)

    async def show_error(self):
        from pages import ErrorPage
        await ErrorPage(self.error).show()
        self.set_result(False)
