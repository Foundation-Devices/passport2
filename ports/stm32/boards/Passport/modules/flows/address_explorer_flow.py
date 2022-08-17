# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# address_explorer_flow.py

import common
import stash
from flows import Flow
from pages import (
    AddressExplorerPage,
    AddressExplorerForward,
    AddressExplorerBackward,
    AddressTypeChooserPage,
)

class AddressExplorerFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.choose_addr_type, name='AddressExplorerFlow')

        self.acct_num = None
        self.is_multisig = False  # TODO
        self.addr_type = None
        self.deriv_path = None
        self.address_number = None
        self.last_qr_version = 0

    async def choose_addr_type(self):
        self.addr_type = await AddressTypeChooserPage().show()
        if self.addr_type is None:
            self.set_result(None)
        else:
            self.goto(self.display_addresses)

    async def display_addresses(self):
        while True:
            address, address_path = self.next_address_with_path()

            result = await AddressExplorerPage(last_version=self.last_qr_version,
                                               address=address,
                                               deriv_path=address_path).show()

            if result is False:
                self.back()
                return
            elif result is True:
                self.set_result(True)
                return
            elif isinstance(result, AddressExplorerForward):
                self.last_qr_version = result.last_version
                self.address_number += 1
                continue
            elif isinstance(result, AddressExplorerBackward):
                self.last_qr_version = result.last_version
                if self.address_number > 0:
                    self.address_number -= 1
                continue

    def next_address_with_path(self):
        from utils import get_next_addr
        from wallets.utils import get_deriv_path_from_addr_type_and_acct

        if self.acct_num is None:
            account = common.ui.get_active_account()
            self.acct_num = account.get('acct_num')

        if self.deriv_path is None:
            self.deriv_path = get_deriv_path_from_addr_type_and_acct(self.addr_type,
                                                                     self.acct_num,
                                                                     self.is_multisig)

        if self.address_number is None:
            self.address_number = get_next_addr(self.acct_num, self.addr_type, False)

        with stash.SensitiveValues() as sv:
            address_path = '{}/{}/{}'.format(self.deriv_path, 0, self.address_number)
            node = sv.derive_path(address_path)

            address = sv.chain.address(node, self.addr_type)

        return address, address_path
