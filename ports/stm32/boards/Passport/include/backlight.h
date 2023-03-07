// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc.
// SPDX-License-Identifier: GPL-3.0-only
//
// Backlight driver for LED

#ifndef STM32_BACKLIGHT_H
#define STM32_BACKLIGHT_H

#include <stdint.h>
#include <stdbool.h>

extern void backlight_init(void);
extern void backlight_minimal_init(void);
extern void backlight_intensity(uint16_t intensity);
extern void backlight_adjust(bool turbo);

#endif  //STM32_BACKLIGHT_H
