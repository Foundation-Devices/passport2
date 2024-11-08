# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# translations.py
#
# Multi-language text utility functions
#

from .tags import T as _T
from .en import EN_TRANSLATIONS

ACTIVE_LANGUAGE = 'en'
TRANSLATIONS = {
    'en': EN_TRANSLATIONS,
}


def t(tag, **kwargs):
    translations = TRANSLATIONS[ACTIVE_LANGUAGE]
    if tag in translations:
        str = translations[tag]
    elif tag in EN_TRANSLATIONS:
        str = EN_TRANSLATIONS[tag]
    else:
        # Error
        return '<UNKNOWN TEXT>'

    if kwargs is not None:
        return str.format(**kwargs)
    else:
        return str


# Get the global active language.
def get_active_language():
    return ACTIVE_LANGUAGE


# Set the global active language.
def set_active_language(language):
    global ACTIVE_LANGUAGE

    # Verify that the requsted language is supported
    if language in TRANSLATIONS.keys():
        ACTIVE_LANGUAGE = language
        return True

    return False


# Re-export the tags
T = _T
