# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# search_for_address_task.py - Task to search a given range of addresses to see if we find a match


async def search_for_address_task(
        on_done,
        path,
        start_address_idx,
        address,
        addr_type,
        multisig_wallet,
        is_change,
        max_to_check,
        reverse):

    import stash
    from errors import Error
    from uasyncio import sleep_ms
    from ubinascii import hexlify as b2a_hex

    # try:
    with stash.SensitiveValues() as sv:
        if multisig_wallet:
            # NOTE: Can't easily reverse order here, so this is slightly less efficient
            for (curr_idx, paths, curr_address, script) in multisig_wallet.yield_addresses(
                start_address_idx,
                max_to_check,
                    change_idx=1 if is_change else 0):
                # print('Multisig: curr_idx={}: paths={} curr_address = {}'.format(curr_idx, paths, curr_address))

                if curr_address == address:
                    # NOTE: Paths are the full paths of the addresses of each signer
                    await on_done(curr_idx, paths, None)
                    return
                await sleep_ms(1)

        else:
            r = range(start_address_idx, start_address_idx + max_to_check)
            if reverse:
                r = reversed(r)

            for curr_idx in r:
                addr_path = '{}/{}/{}'.format(path, is_change, curr_idx)  # Zero for non-change address
                # print('Singlesig: addr_path={}'.format(addr_path))
                node = sv.derive_path(addr_path)
                print(b2a_hex(node.public_key()))
                curr_address = sv.chain.address(node, addr_type)
                # print('           curr_idx={}: path={} addr_type={} curr_address = {}'.format(curr_idx, addr_path,
                #       addr_type, curr_address))
                print("path: {}, address: {}".format(addr_path, curr_address))
                if curr_address == address:
                    await on_done(curr_idx, addr_path, None)
                    return
                await sleep_ms(1)

    await on_done(-1, None, Error.ADDRESS_NOT_FOUND)
    # except Exception as e:
    #     # print('EXCEPTION: e={}'.format(e))
    #     # Any address handling exceptions result in no address found
    #     await on_done(-1, None, Error.ADDRESS_NOT_FOUND)
