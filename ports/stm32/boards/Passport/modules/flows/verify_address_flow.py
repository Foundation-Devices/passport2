# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# verify_address_flow.py - Scan an address QR code and verify that it belongs to this Passport.


from flows import Flow
from common import ui
import microns


_RECEIVE_ADDR = const(0)
_CHANGE_ADDR = const(1)
_NUM_TO_CHECK = const(50)


class VerifyAddressFlow(Flow):
    def __init__(self, sig_type=None, multisig_wallet=None):
        if sig_type is not None:
            initial_state = self.scan_address
        else:
            initial_state = self.choose_sig_type

        super().__init__(initial_state=initial_state, name='VerifyAddressFlow')
        self.account = ui.get_active_account()
        self.acct_num = self.account.get('acct_num')
        self.sig_type = sig_type
        self.multisig_wallet = multisig_wallet
        self.is_multisig = False
        self.found_addr_idx = None
        self.found_is_change = False
        self.addr_type = None
        self.deriv_path = None
        self.address = None

        # These can't be properly initialized until we know more about the address
        self.low_range = None
        self.high_range = None
        self.low_size = [0, 0]
        self.high_size = [0, 0]

    async def choose_sig_type(self):
        from pages import SinglesigMultisigChooserPage
        from multisig_wallet import MultisigWallet
        from common import settings

        xfp = settings.get('xfp')
        multisigs = MultisigWallet.get_by_xfp(xfp)

        if len(multisigs) == 0:
            self.sig_type = 'single-sig'
            self.goto(self.scan_address, save_curr=False)  # Don't save this since we're skipping this state
        else:
            result = await SinglesigMultisigChooserPage(
                initial_value=self.sig_type, multisigs=multisigs).show()
            if result is None:
                if not self.back():
                    self.set_result(False)
                return

            (self.sig_type, self.multisig_wallet) = result
            # print('sig_type={}'.format(self.sig_type))
            # print('multisig_wallet={}'.format(self.multisig_wallet))
            self.goto(self.scan_address)

    async def scan_address(self):
        import chains
        from pages import ErrorPage
        from flows import ScanQRFlow
        from wallets.utils import get_addr_type_from_address, get_deriv_path_from_addr_type_and_acct
        from utils import is_valid_btc_address, get_next_addr
        from data_codecs.qr_type import QRType
        from common import settings

        result = await ScanQRFlow(qr_types=[QRType.QR],
                                  data_description='a Bitcoin address').run()

        if result is None:
            if not self.back():
                self.set_result(False)
                return
            return

        # print('result={}'.format(result))
        self.address = result

        # Simple check on the data type first
        chain = chains.current_chain()
        self.address, is_valid_btc = is_valid_btc_address(self.address)
        if not is_valid_btc:
            await ErrorPage("Not a valid {} address.".format(chain.name)).show()
            return

        # Get the address type from the address
        self.is_multisig = self.sig_type == 'multisig'

        # print('address={} acct_num={} is_multisig={}'.format(address, self.acct_num, is_multisig))
        self.addr_type = get_addr_type_from_address(self.address, self.is_multisig)
        self.deriv_path = get_deriv_path_from_addr_type_and_acct(self.addr_type, self.acct_num, self.is_multisig)

        # Setup initial ranges
        xfp = settings.get('xfp')
        a = [get_next_addr(self.acct_num,
                           self.addr_type,
                           xfp,
                           chain.b44_cointype,
                           False),
             get_next_addr(self.acct_num,
                           self.addr_type,
                           xfp,
                           chain.b44_cointype,
                           True)]
        self.low_range = [(a[_RECEIVE_ADDR], a[_RECEIVE_ADDR]), (a[_CHANGE_ADDR], a[_CHANGE_ADDR])]
        self.high_range = [(a[_RECEIVE_ADDR], a[_RECEIVE_ADDR]), (a[_CHANGE_ADDR], a[_CHANGE_ADDR])]

        self.goto(self.search_for_address)

    def finalize(self, addr_idx, is_change):
        self.found_addr_idx = addr_idx
        self.found_is_change = is_change == 1
        self.goto(self.found)

    async def search_for_address(self):
        from tasks import search_for_address_task
        from utils import get_prev_address_range, get_next_address_range, spinner_task

        # Try next batch of addresses
        for is_change in range(0, 2):
            self.low_range[is_change], self.low_size[is_change] = get_prev_address_range(self.low_range[is_change],
                                                                                         _NUM_TO_CHECK // 2)
            self.high_range[is_change], self.high_size[is_change] = get_next_address_range(
                self.high_range[is_change], _NUM_TO_CHECK - self.low_size[is_change])

        addr_idx = -1
        is_change = 0

        (addr_idx, path_info, error) = await spinner_task(
            'Searching Addresses',
            search_for_address_task,
            min_duration_ms=0,
            args=[self.deriv_path,
                  0,
                  self.address,
                  self.addr_type,
                  self.multisig_wallet,
                  is_change,
                  1,
                  True])

        if addr_idx >= 0:
            self.finalize(addr_idx, is_change)
            return

        for is_change in range(0, 2):
            # print('CHECKING: low_range={}  low_size={}'.format(self.low_range, self.low_size))
            # Check downwards
            if self.low_size[is_change] > 0:
                (addr_idx, path_info, error) = await spinner_task(
                    'Searching Addresses',
                    search_for_address_task,
                    min_duration_ms=0,
                    args=[self.deriv_path,
                          self.low_range[is_change][0],
                          self.address,
                          self.addr_type,
                          self.multisig_wallet,
                          is_change,
                          self.low_size[is_change],
                          True])

            # Exit if already found
            if addr_idx >= 0:
                break

            # print('CHECKING: high_range={}  high_size={}'.format(self.high_range, self.high_size))
            # Check upwards
            (addr_idx, path_info, error) = await spinner_task(
                'Searching Addresses',
                search_for_address_task,
                min_duration_ms=0,
                args=[self.deriv_path,
                      self.high_range[is_change][0],
                      self.address,
                      self.addr_type,
                      self.multisig_wallet,
                      is_change,
                      self.high_size[is_change],
                      True])

            if addr_idx >= 0:
                break

        if addr_idx >= 0:
            self.finalize(addr_idx, is_change)
        else:
            self.goto(self.not_found)

    async def not_found(self):
        from pages import ErrorPage, LongErrorPage
        import passport

        # Address was not found in that batch of 100, so offer to keep searching
        msg = 'Address Not Found\nRanges Checked:\n'

        # Build a merged range for receive and one for change addresses
        merged_range = []
        for is_change in range(0, 2):
            msg += '{} addrs: {}-{}{}'.format(
                'Change' if is_change == 1 else 'Receive', self.low_range[is_change][0],
                self.high_range[is_change][1] - 1, '' if is_change == 1 else '\n')

        msg += '\n\nContinue searching?'

        page_class = ErrorPage if passport.IS_COLOR else LongErrorPage

        result = await page_class(msg, left_micron=microns.Cancel, right_micron=microns.Checkmark).show()
        if result:
            self.goto(self.search_for_address)
        else:
            self.set_result(False)

    async def found(self):
        from pages import SuccessPage, LongSuccessPage
        from utils import save_next_addr, format_btc_address, stylize_address
        import passport
        from common import settings
        import chains
        from public_constants import MARGIN_FOR_ADDRESSES
        import lvgl as lv

        # Remember where to start from next time
        save_next_addr(self.acct_num,
                       self.addr_type,
                       self.found_addr_idx,
                       settings.get('xfp'),
                       chains.current_chain().b44_cointype,
                       self.found_is_change)
        address = stylize_address(self.address)

        msg = '''{}

{} Address {}'''.format(
            address,
            'Change' if self.found_is_change == 1 else 'Receive',
            self.found_addr_idx)

        await SuccessPage(text=msg,
                          margins=MARGIN_FOR_ADDRESSES,
                          custom_verified_icon=True).show()
        self.set_result(True)
