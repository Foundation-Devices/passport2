# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# magic_scan_validate_address_flow.py - Validate the given address

from flows import Flow


class MagicScanValidateAddressFlow(Flow):
    def __init__(self, data=None):
        super().__init__(initial_state=self.xxx, name='MagicScanValidateAddressFlow')
        self.data = data

    async def xxx(self):
        pass
