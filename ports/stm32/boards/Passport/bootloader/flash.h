// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
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

#include "stm32h7xx_hal.h"

#include "secresult.h"

// Details of the OTP area. 64-bit slots.
#define OPT_FLASH_BASE 0x1FFF7000
#define NUM_OPT_SLOTS 128

#define USER_SETTINGS_FLASH_ADDR 0x81E0000

static inline bool flash_is_security_level2(void) {
    return ((FLASH->OPTSR_CUR & FLASH_OPTSR_RDP_Msk) == OB_RDP_LEVEL_2);
}

// generial purpose flash functions
extern void      flash_lock(void);
extern void      flash_unlock(void);
extern int       flash_burn(uint32_t flash_address, uint32_t data_address);
extern int       flash_sector_erase(uint32_t address);
extern void      flash_test(void);
extern secresult flash_first_boot(void);
extern void      flash_lockdown_hard(void);
extern secresult flash_is_programmed(void);
extern secresult flash_is_locked(void);

// EOF
