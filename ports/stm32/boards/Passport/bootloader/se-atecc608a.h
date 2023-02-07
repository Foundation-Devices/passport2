// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
// Copyright 2020 - Foundation Devices Inc.
//

#ifndef _SECURE_ELEMENT_ATECC608A_H_
#define _SECURE_ELEMENT_ATECC608A_H_

#include "secrets.h"

extern void    se_setup(void);
extern int     se_setup_config(rom_secrets_t* secrets);
extern uint8_t se_get_gpio(void);
extern int     se_set_gpio(int state);
extern int     se_set_gpio_secure(uint8_t* digest);
extern int     se_program_board_hash(uint8_t* previous_hash, uint8_t* new_hash);
extern bool    se_valid_secret(uint8_t* secret);

#endif  //_SECURE_ELEMENT_ATECC608A_H_
