# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# get_security_words_task.py - Task to get the security words associated with a given PIN attempt.

async def get_security_words_task(on_done, prefix):
    from pincodes import PinAttempt

    security_words = PinAttempt.anti_phishing_words(prefix)

    await on_done(security_words, None)
