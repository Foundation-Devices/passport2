# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_derived_key_details_flow.py - Show user details of a derived key

from flows.flow import Flow


class ViewDerivedKeyDetailsFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.show_overview, name='ViewMultisigDetailsFlow')
        self.key = context

    async def show_overview(self):
        from utils import recolor
        from styles.colors import HIGHLIGHT_TEXT_HEX
        from pages.long_text_page import LongTextPage
        from pages.error_page import ErrorPage
        from derived_key import get_key_type_from_tn
        import microns

        key_type = get_key_type_from_tn(self.key['tn'])

        if not key_type:
            await ErrorPage("Invalid key type number: {}".format(self.key['tn'])).show()
            self.set_result(False)
            return

        msg = "\n{}\n{}\n\n{}\n{}".format(recolor(HIGHLIGHT_TEXT_HEX, 'Key Type'),
                                          key_type['title'],
                                          recolor(HIGHLIGHT_TEXT_HEX, 'Key Index'),
                                          self.key['index'])

        await LongTextPage(card_header={'title': self.key['name']},
                           text=msg,
                           left_micron=None,
                           right_micron=microns.Checkmark,
                           centered=True).show()
        self.set_result(True)
