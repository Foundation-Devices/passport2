# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# save_seed_task.py - Task to save a given seed

from stash import SecretStash


async def save_seed_task(on_done, seed_bits):
    from common import pa
    import stash

    secret = SecretStash.encode(seed_bits=seed_bits)

    pa.change(new_secret=secret)

    # Recapture XFP, etc. for new secret
    await pa.new_main_secret(secret)

    # Check and reload secret
    pa.reset()
    pa.login()

    with stash.SensitiveValues() as sv:
        sv.capture_xpub(save=True)

    await on_done(None)
