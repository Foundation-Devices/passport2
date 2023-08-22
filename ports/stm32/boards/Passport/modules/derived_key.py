# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# derived_key.py - Different keys can be derived from the root bitcoin key

import lvgl as lv
from tasks import bip85_24_word_seed_task, bip85_12_word_seed_task, nostr_key_task
from menus import nostr_menu

# Each key generation task must take index as args, whether or not they use it.
# Each task must return ({'priv', <private key>, etc.}, None)
# tn stands for Type Number
key_types = [
    {'tn': 1,
     'title': '12 Word Seed',
     'icon': 'ICON_SEED',
     'indexed': True,
     'words': True,
     'task': bip85_12_word_seed_task},
    {'tn': 0,
     'title': '24 Word Seed',
     'icon': 'ICON_SEED',
     'indexed': True,
     'words': True,
     'task': bip85_24_word_seed_task},
    {'tn': 2,
     'title': 'Nostr Key',
     'icon': 'ICON_NOSTR',
     'indexed': True,
     'words': False,
     'task': nostr_key_task,
     'continue_text': 'post on your behalf',
     'menu': nostr_menu},
]


def get_key_type_from_tn(tn):
    for key_type in key_types:
        if key_type['tn'] == tn:
            return key_type
    return None

# This is unused, but it's an example of the schema
# DEFAULT_DERIVED_KEY = {'name': 'First',
#                        'index': 0,
#                        'tn': 0,
#                        'xfp': <binary xfp>,
#                        'hidden': False}
