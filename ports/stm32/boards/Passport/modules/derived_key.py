# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# derived_key.py - Different keys can be derived from the root bitcoin key

import lvgl as lv
from tasks import bip85_seed_task, nostr_key_task

# Each key generation task must take num_words and index as args, whether or not they use them.
key_types = {
    'Bitcoin Child Seed': {'icon': lv.ICON_BITCOIN,
                           'indexed': True,
                           'words': True,
                           'task': bip85_seed_task},
    'Nostr Key': {'icon': lv.ICON_ONE_KEY,
                  'indexed': False,
                  'words': False,
                  'task': nostr_key_task},
}

# This is unused, but it's an example of the schema
# DEFAULT_DERIVED_KEY = {'name': 'First', 'index': 0, 'type': 'BIP85', 'xfp': <binary xfp>}
