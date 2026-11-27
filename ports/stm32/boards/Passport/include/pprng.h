// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
 * and is covered by GPLv3 license found in COPYING.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

void     rng_setup(void);
bool     rng_try_sample(uint32_t* result);
uint32_t rng_sample(void);
void     rng_buffer(uint8_t* result, int len);
void     rng_fatal_error(void) __attribute__((noreturn));
