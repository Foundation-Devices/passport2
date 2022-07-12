// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef __FREQUENCY_H__
#define __FREQUENCY_H__

#include <stdbool.h>

extern void frequency_update_console_uart(void);
extern void frequency_turbo_toggle(bool enable);
extern void frequency_turbo(bool enable);

#endif  // __FREQUENCY_H__
