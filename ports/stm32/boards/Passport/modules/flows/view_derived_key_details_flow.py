# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_derived_key_details_flow.py - Show user details of a derived key

from flows import Flow


class ViewDerivedKeyDetailsFlow(Flow):
    def __init__(self, context=None):
        super().__init__(initial_state=self.show_overview, name='ViewMultisigDetailsFlow')
        self.key = context

    async def show_overview(self):
        from utils import recolor
        from styles.colors import HIGHLIGHT_TEXT_HEX
        from pages import LongTextPage
        from derived_key import key_types
        import microns

        msg = "\n{}\n{}\n\n{}\n{}".format(recolor(HIGHLIGHT_TEXT_HEX, 'Key Type'),
                                          key_types[self.key['type']]['title'],
                                          recolor(HIGHLIGHT_TEXT_HEX, 'Key Index'),
                                          self.key['index'])

        await LongTextPage(card_header={'title': self.key['name']},
                           text=msg,
                           left_micron=None,
                           right_micron=microns.Checkmark,
                           centered=True).show()
        self.set_result(True)