# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# export.py - Functions for exporting data from Passport.


import chains
import stash
import trezorcrypto
import ujson
from ubinascii import hexlify as b2a_hex
from uio import StringIO
from utils import xfp2str


def ms_has_master_xfp(xpubs):
    from common import settings
    master_xfp = settings.get('xfp', None)

    for xpub in xpubs:
        xfp = xpub[0]
        # print('ms_has_master_xfp: xfp={} master_xfp={}'.format(xfp, master_xfp))
        if xfp == master_xfp:
            # print('Including this one')
            return True

    # print('EXCLUDING this one')
    return False


def render_backup_contents():
    # simple text format:
    #   key = value
    # or #comments
    # but value is JSON
    from common import settings, pa, system
    from utils import get_month_str
    from utime import localtime

    rv = StringIO()

    def COMMENT(val=None):
        if val:
            rv.write('\n# %s\n' % val)
        else:
            rv.write('\n')

    def ADD(key, val):
        rv.write('%s = %s\n' % (key, ujson.dumps(val)))

    rv.write('# Passport backup file! DO NOT CHANGE.\n')

    chain = chains.current_chain()

    COMMENT('Private Key Details: ' + chain.name)

    with stash.SensitiveValues(for_backup=True) as sv:

        if sv.mode == 'words':
            ADD('mnemonic', trezorcrypto.bip39.from_data(sv.raw))

        if sv.mode == 'master':
            ADD('bip32_master_key', b2a_hex(sv.raw))

        ADD('chain', chain.ctype)
        ADD('xfp', xfp2str(sv.get_xfp()))
        ADD('xprv', chain.serialize_private(sv.node))
        ADD('xpub', chain.serialize_public(sv.node))

        # BTW: everything is really a duplicate of this value
        ADD('raw_secret', b2a_hex(sv.secret).rstrip(b'0'))

    COMMENT('Firmware Version (informational):')
    (fw_version, _, _, _, fw_date) = system.get_software_info()

    ADD('fw_version', fw_version)
    ADD('fw_date', fw_date)

    COMMENT('User Preferences:')

    # user preferences - sort so that accounts is processed before multisig
    multisig_ids = []
    settings_dict = None
    if settings.temporary_mode:
        settings_dict = settings.temporary_settings
    else:
        settings_dict = settings.current
    for k, v in sorted(settings_dict.items()):
        # print('render handling key "{}"'.format(k))
        if k[0] == '_':
            continue        # debug stuff in simulator
        if k == 'xpub':
            continue        # redundant, and wrong if bip39pw
        if k == 'xfp':
            continue         # redundant, and wrong if bip39pw

        # if k == 'accounts':
        #     # Filter out accounts that have a passphrase
        #     print('Filtering out accounts that have a bip39_hash')
        #     v = list(filter(lambda acct: acct.get('bip39_hash', '') == '', v))
        #     multisig_ids = [acct.get('multisig_id', None) for acct in v]
        #     multisig_ids = list(filter(lambda ms: ms != None, multisig_ids))  # Don't include None entries
        #     print('multisig_ids={}'.format(multisig_ids))
        #
        if k == 'multisig':
            # Only backup multisig entries that have the master XFP - plausible deniability in your backups
            # "Passphrase wallets? I don't have any passphrase wallets!"
            # print('ms={}'.format(v))
            v = list(filter(lambda ms: ms_has_master_xfp(ms[2]), v))

        ADD('setting.' + k, v)

    rv.write('\n# EOF\n')

    return rv.getvalue()
