// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//

#ifndef _SECURE_ELEMENT_ATECC608A_H_
#define _SECURE_ELEMENT_ATECC608A_H_

#include "storage.h"

// Test if chip responds correctly, and do some setup; returns error string if fail.
bool se_probe();

// Pick a fresh random number.
int se_random(uint8_t randout[32]);

// Roll (derive) a key using random number we forget. One way!
int se_destroy_key(int keynum);

// Do Info(p1=2) command, and return result; p1=3 if get_gpio
uint16_t se_get_info(void);

// Bits in Info(p1=2) response
#define I_TempKey_KeyId(n) ((n >> 8) & 0x0f)
#define I_TempKey_SourceFlag(n) ((n >> 12) & 0x1)
#define I_TempKey_GenDigData(n) ((n >> 13) & 0x1)
#define I_TempKey_GenKeyData(n) ((n >> 14) & 0x1)
#define I_TempKey_NoMacFlag(n) ((n >> 15) & 0x1)

#define I_EEPROM_RNG(n) ((n >> 0) & 0x1)
#define I_SRAM_RNG(n) ((n >> 1) & 0x1)
#define I_AuthValid(n) ((n >> 2) & 0x1)
#define I_AuthKey(n) ((n >> 3) & 0x0f)
#define I_TempKey_Valid(n) ((n >> 7) & 0x1)

// Do a dance that unlocks various keys. Return T if it fails.
int se_unlock_ip(uint8_t keynum, const uint8_t secret[32]);

// Perform HMAC on the chip, using a particular key.
//int se_hmac(uint8_t keynum, const uint8_t *msg, uint16_t msg_len, uint8_t digest[32]);
int se_hmac32(uint8_t keynum, uint8_t msg[32], uint8_t digest[32]);

// Load TempKey with indicated value, exactly.
int se_load_nonce(uint8_t nonce[32]);

// Return the serial number.
// Nine bytes of serial number. First 2 bytes always 0x0123 and last one 0xEE
int se_get_serial(uint8_t serial[6]);

// Call this if possible mitm is detected.
extern void fatal_mitm(void) __attribute__((noreturn));

// Perform many key iterations and read out the result. Designed to be slow.
int se_stretch_iter(const uint8_t start[32], uint8_t end[32], int iterations);

// Mix in (via HMAC) the contents of a specific key on the device.
int se_mixin_key(uint8_t keynum, uint8_t start[32], uint8_t end[32]);

#endif  //_SECURE_ELEMENT_ATECC608A_H_
