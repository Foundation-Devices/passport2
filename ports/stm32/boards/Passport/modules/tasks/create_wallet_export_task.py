
# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# create_wallet_export_task.py - Run the function that will generate the wallet export data


async def create_wallet_export_task(on_done, export_fn, sw_wallet, addr_type,
                                    acct_num, multisig, legacy, export_mode,
                                    qr_type):
    '''This is in a task as some exports could take some time due to cryptography.'''
    (data, acct_info) = export_fn(
        sw_wallet=sw_wallet, addr_type=addr_type, acct_num=acct_num,
        multisig=multisig, legacy=legacy, export_mode=export_mode,
        qr_type=qr_type)

    await on_done(data, acct_info, None)
