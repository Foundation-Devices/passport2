# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# address_explorer_flow.py - View addresses related to the current account

from flows import Flow


class AddressExplorerFlow(Flow):
    NAV_VALS = {
        'up': -10,
        'down': 10,
        'left': -1,
        'right': 1,
    }

    def __init__(self):
        from common import ui

        super().__init__(initial_state=self.choose_sig_type, name='AddressExplorerFlow')
        self.account = ui.get_active_account()
        self.acct_num = self.account.get('acct_num')
        self.sig_type = None
        self.multisig_wallet = None
        self.is_multisig = False
        self.addr_type = None
        self.deriv_path = None
        self.is_change = None
        self.index = 0

    async def choose_sig_type(self):
        from pages import SinglesigMultisigChooserPage
        from multisig_wallet import MultisigWallet
        from common import settings

        xfp = settings.get('xfp')
        multisigs = MultisigWallet.get_by_xfp(xfp)

        if len(multisigs) == 0:
            self.sig_type = 'single-sig'
            self.goto(self.choose_addr_type, save_curr=False)  # Skipping this state
            return

        result = await SinglesigMultisigChooserPage(
            initial_value=self.sig_type, multisigs=multisigs).show()

        if result is None:
            self.set_result(False)
            return

        (self.sig_type, self.multisig_wallet) = result
        self.is_multisig = self.sig_type == 'multisig'
        if not self.is_multisig:
            self.goto(self.choose_addr_type)
            return

        self.goto(self.prepare)

    async def choose_addr_type(self):
        from pages import AddressTypeChooserPage
        from wallets.utils import get_deriv_path_from_addr_type_and_acct

        result = await AddressTypeChooserPage().show()

        if not result:
            self.back()
            return

        self.addr_type = result
        self.deriv_path = get_deriv_path_from_addr_type_and_acct(self.addr_type, self.acct_num, self.is_multisig)
        self.goto(self.choose_change)

    async def choose_change(self):
        from pages import YesNoChooserPage

        result = await YesNoChooserPage(text="\nExplore receive or change addresses?",
                                        yes_text="Receive",
                                        no_text="Change").show()

        if result is None:
            self.back()
            return

        self.is_change = not result
        self.goto(self.prepare)

    async def prepare(self):
        from common import settings
        import chains
        from utils import get_next_addr
        from pages import LongTextPage, ErrorPage
        from flows import SeriesOfPagesFlow
        import microns

        text1 = '''\nUse the directional pad to navigate addresses.\n
Up: -10
Down: +10
Left: -1
Right: +1'''

        result = await LongTextPage(text=text1, centered=True).show()

        if not result:
            self.back()
            return

        messages = [{'text': 'Passport cannot know if displayed addresses have been used.',
                     'left_micron': microns.Back,
                     'right_micron': microns.Forward},
                    {'text': 'Connect Passport with a wallet like Envoy to avoid reusing addresses.',
                     'left_micron': microns.Back}]

        result2 = await SeriesOfPagesFlow(ErrorPage, messages).run()

        if not result2:
            return

        self.xfp = settings.get('xfp')
        self.chain = chains.current_chain()
        self.index = get_next_addr(self.acct_num,
                                   self.addr_type,
                                   self.xfp,
                                   self.chain.b44_cointype,
                                   self.is_change)

        self.goto(self.explore)

    async def explore(self):
        from utils import stylize_address, get_single_address
        import passport
        from pages import ShowQRPage, AddressExplorerPage
        import microns

        try:
            self.address = get_single_address(self.xfp,
                                              self.chain,
                                              self.index,
                                              self.is_multisig,
                                              self.multisig_wallet,
                                              self.is_change,
                                              self.deriv_path,
                                              self.addr_type)
        except Exception as e:
            # TODO: make error page
            self.set_result(False)
            return

        nice_address = stylize_address(self.address)

        msg = '''{} Address {}

{}'''.format('Change' if self.is_change else 'Receive',
             self.index,
             nice_address)

        while True:
            result = await AddressExplorerPage(msg,
                                               left_micron=microns.Cancel,
                                               right_micron=microns.ScanQR).show()

            if not result:
                self.set_result(True)
                return
            elif result is True:
                await ShowQRPage(qr_data=self.address,
                                 left_micron=None,
                                 right_micron=microns.Checkmark).show()
            else:
                self.index = max(0, self.index + self.NAV_VALS[result])
                break
