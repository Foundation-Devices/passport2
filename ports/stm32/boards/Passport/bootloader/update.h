// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//

#pragma once

#include <stdint.h>
#include "fwheader.h"

extern void      update_firmware(void);
extern secresult is_firmware_update_present(void);
extern secresult is_user_signed_firmware_installed(void);
extern void      copy_firmware_from_sd_to_spi(passport_firmware_header_t* hdr);
extern void      clear_update_from_spi_flash(uint32_t total_size);
