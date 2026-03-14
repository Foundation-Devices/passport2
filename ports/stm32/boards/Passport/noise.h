// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#pragma once

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>

// Flags to select which entroy sources to combine
#define NOISE_AVALANCHE_SOURCE  (1 << 0)
#define NOISE_MCU_RNG_SOURCE    (1 << 1)
#define NOISE_SE_RNG_SOURCE     (1 << 2)
#define NOISE_ALL               (NOISE_AVALANCHE_SOURCE | NOISE_MCU_RNG_SOURCE | \
                                 NOISE_SE_RNG_SOURCE)

void noise_enable();
void noise_disable();
bool noise_get_random_uint16(uint16_t* result);
bool noise_get_random_bytes(uint8_t sources, void* buf, size_t buf_len);