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
        self.curr_idx = 0

    async def choose_sig_type(self):
        from pages import SinglesigMultisigChooserPage
        from multisig_wallet import MultisigWallet
        from common import settings

        xfp = settings.get('xfp')
        multisigs = MultisigWallet.get_by_xfp(xfp)

        if len(multisigs) == 0:
            self.sig_type = 'single-sig'
            self.goto(self.choose_addr_type, save_curr=False)  # Skipping this state
        else:
            result = await SinglesigMultisigChooserPage(
                initial_value=self.sig_type, multisigs=multisigs).show()

            if result is None:
                self.set_result(False)
                return

            (self.sig_type, self.multisig_wallet) = result

            self.is_multisig = self.sig_type == 'multisig'
            self.goto(self.choose_addr_type)

    async def choose_addr_type(self):
        from pages import AddressTypeChooserPage
        from wallets.utils import get_deriv_path_from_addr_type_and_acct

        result = await AddressTypeChooserPage().show()

        if result is None:
            self.back()
            return

        self.addr_type = result
        self.deriv_path = get_deriv_path_from_addr_type_and_acct(self.addr_type, self.acct_num, self.is_multisig)
        self.goto(self.choose_change)

    async def choose_change(self):
        from pages import YesNoChooserPage

        result = await YesNoChooserPage(text="Explore normal or change addresses?",
                                        yes_text="Normal",
                                        no_text="Change").show()

        if result is None:
            self.back()
            return

        self.is_change = not result
        self.goto(self.explore)

    async def explore(self):
        import chains
        from utils import get_next_addr, format_btc_address
        from common import settings
        import stash
        import passport
        from pages import SuccessPage, LongSuccessPage
        import microns

        xfp = settings.get('xfp')
        chain = chains.current_chain()
        index = get_next_addr(self.acct_num,
                              self.addr_type,
                              xfp,
                              chain.b44_cointype,
                              self.is_change)

        while True:
            # TODO: break this into a util function
            address = None
            try:
                with stash.SensitiveValues() as sv:
                    if self.is_multisig:
                        (curr_idx, paths, address, script) = list(self.multisig_wallet.yield_addresses(
                            start_idx=index,
                            count=1,
                            change_idx=1 if self.is_change else 0))[0]
                    else:
                        addr_path = '{}/{}/{}'.format(self.deriv_path, 1 if self.is_change else 0, index)
                        print(addr_path)
                        node = sv.derive_path(addr_path)
                        address = sv.chain.address(node, self.addr_type)
            except Exception as e:
                # TODO: make error page
                break
            # TODO: use nice new address formatting
            nice_address = format_btc_address(address, self.addr_type)

            msg = '''{}

{} Address {}'''.format(
                nice_address,
                'Change' if self.is_change else 'Receive',
                index)

            # TODO: make a new page that allows navigation
            page_class = SuccessPage if passport.IS_COLOR else LongSuccessPage
            result = await page_class(msg, left_micron=microns.Cancel).show()

            if not result:
                break
            else:
                index += 1

        self.set_result(True)
