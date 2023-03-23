# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test that the translation module works.

import sys
import os

sys.path.insert(1, os.path.join(sys.path[0], '..'))


def test_change_active_language():
    from translations import t, T, set_active_language, get_active_language

    assert set_active_language('en')
    assert get_active_language() == 'en'

    # The value of these messages will be always these so we can reliably test
    # here if a basic Yes/No is translated.
    #
    # NOTE: If these values are changed on the translations please update this
    # test!
    assert t(T.DEFAULT_YES_BUTTON_LABEL) == "Yes"
    assert t(T.DEFAULT_NO_BUTTON_LABEL) == "No"

    assert set_active_language('es')
    assert get_active_language() == 'es'

    assert t(T.DEFAULT_YES_BUTTON_LABEL) == "Sí"
    assert t(T.DEFAULT_NO_BUTTON_LABEL) == "No"

    # Restore it.
    assert set_active_language('en')


def test_fallback_works():
    from translations import t, T, set_active_language

    # Verify that messages that don't need to be translated for some languages
    # correctly fall back to the original english translation (this avoid duplicate
    # strings).
    #
    # NOTE: If ever FOUNDATION_CO is translated to spanish update this test.
    assert set_active_language('es')
    foundation_co_es = t(T.FOUNDATION_CO)

    assert set_active_language('en')
    foundation_co_en = t(T.FOUNDATION_CO)

    assert foundation_co_es == foundation_co_en
