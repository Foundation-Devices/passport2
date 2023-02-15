# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# derived_key.py - Different keys can be derived from the root bitcoin key

import lvgl as lv
from tasks import bip85_seed_task, nostr_key_task

key_types = {
    'BIP85': {'icon': lv.ICON_BITCOIN, 'task': bip85_seed_task},
    'Nostr': {'icon': lv.ICON_ONE_KEY, 'task': nostr_key_task},
}

# This is unused, but it's an example of the schema
# DEFAULT_DERIVED_KEY = {'name': 'First', 'index': 0, 'passphrase': False, 'type': 'BIP85'}
