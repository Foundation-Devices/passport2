// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef __GPIO_H__
#define __GPIO_H__

void gpio_init(void);
__attribute__((noreturn)) void passport_reset(void);
__attribute__((noreturn)) void passport_shutdown(void);

#endif  // __GPIO_H__
