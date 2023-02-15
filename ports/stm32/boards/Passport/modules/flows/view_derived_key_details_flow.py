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

        msg = "{}\n{}\n\n{}\n{}".format(recolor(HIGHLIGHT_TEXT_HEX, 'Key Type'),
                                        self.key['type'],
                                        recolor(HIGHLIGHT_TEXT_HEX, 'Key Index'),
                                        self.key['index'])

        if self.key['passphrase']:
            msg += '''\n
{}\nThis key was generated while a passphrase was applied. \
Re-apply this passphrase to accurately export this key.''' \
                   .format(recolor(HIGHLIGHT_TEXT_HEX, 'Passphrase'))

        await LongTextPage(card_header={'title': self.key['name']}, text=msg, centered=True).show()
        self.set_result(True)
