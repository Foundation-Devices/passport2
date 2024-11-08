# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# new_seed_task.py - Task to create a new random seed

import common
import trezorcrypto
from utils import b2a_hex


async def new_seed_task(on_done, seed_length):
    seed = bytearray(32)
    common.noise.random_bytes(seed, common.noise.ALL)

    # Hash to mitigate any potential bias in RNG sources
    seed = trezorcrypto.sha256(seed).digest()

    # Math to convert number of words to number of bytes
    seed = seed[0:((seed_length // 3) * 4)]

    # print('create_new_wallet_seed(): New seed = {}'.format(b2a_hex(seed)))

    await on_done(seed, None)
