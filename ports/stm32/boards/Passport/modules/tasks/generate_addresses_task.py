# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# generate_addresses_task.py - Generate a set of addresses for the given account

from wallets.utils import derive_address, get_deriv_path_from_addr_type_and_acct


async def generate_addresses_task(on_done, start, end, addr_type, acct_num, ms_wallet):
    # print('addr_type={} acct_num={} ms_wallet={}'.format(addr_type, acct_num, ms_wallet))

    entries = []
    for i in range(start, end):
        deriv_path = get_deriv_path_from_addr_type_and_acct(addr_type, acct_num, ms_wallet is not None)
        entry = derive_address(deriv_path, i, addr_type, ms_wallet)
        entries.append(entry)

    await on_done(entries, None)
