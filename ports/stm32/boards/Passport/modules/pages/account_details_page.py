# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# account_details_page.py - Show a page with information for the current account.

import lvgl as lv
from pages import LongTextPage
import microns
from styles.colors import HIGHLIGHT_TEXT_HEX


class AccountDetailsPage(LongTextPage):
    def __init__(
            self,
            card_header=None,
            statusbar=None,
            left_micron=microns.Back,
            right_micron=microns.Checkmark):
        from common import ui
        from utils import recolor
        import stash
        import chains
        from public_constants import AF_P2WPKH
        from wallets.utils import get_bip_num_from_addr_type

        self.account = ui.get_active_account()

        mode = get_bip_num_from_addr_type(AF_P2WPKH, False)

        chain = chains.current_chain()

        with stash.SensitiveValues() as sv:
            deriv_path = "m/{mode}'/{coin}'/{acct}'".format(
                mode=mode,
                coin=chain.b44_cointype,
                acct=self.account.get('acct_num'))

        msg = '''
{acct_name_title}
{acct_name}

{acct_num_title}
{acct_num}

{deriv_title}
{deriv}'''.format(
            acct_name_title=recolor(HIGHLIGHT_TEXT_HEX, 'Account Name'),
            acct_name=self.account.get('name'),
            acct_num_title=recolor(HIGHLIGHT_TEXT_HEX, 'Account Number'),
            acct_num=self.account.get('acct_num'),
            deriv_title=recolor(HIGHLIGHT_TEXT_HEX, 'Envoy Derivation'),
            deriv=deriv_path
        )
        super().__init__(
            text=msg,
            card_header=card_header,
            centered=True,
            statusbar=statusbar,
            left_micron=left_micron,
            right_micron=right_micron)
