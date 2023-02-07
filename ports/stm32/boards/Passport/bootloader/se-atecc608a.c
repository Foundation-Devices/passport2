// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//

#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>

#include "flash.h"
#include "hash.h"
#include "pprng.h"
#include "se-atecc608a.h"
#include "se-config.h"
#include "se.h"
#include "sha256.h"
#include "fwheader.h"
#include "utils.h"

static int se_write_data_slot(int slot_num, uint8_t* data, int len, bool lock_it) {
    if ((len < 32) || (len > 416) || (lock_it && slot_num == 8)) {
        return -1;
    }

    for (int blk = 0, xlen = len; xlen > 0; blk++, xlen -= 32) {
        int rc;

        // have to write each "block" of 32-bytes, separately
        // zone => data
        se_write(OP_Write, 0x80 | 2, (blk << 8) | (slot_num << 3), data + (blk * 32), 32);

        rc = se_read1();
        if (rc < 0) return -1;
    }

    if (lock_it) {
        // Assume 36/72-byte long slot, which will be partially written, and rest
        // should be ones.
        const int slot_len = (slot_num <= 7) ? 36 : 72;
        uint8_t   copy[slot_len];

        memset(copy, 0xff, slot_len);
        memcpy(copy, data, len);

        // calc expected CRC
        uint8_t crc[2] = {0, 0};
        se_crc16_chain(slot_len, copy, crc);

        // do the lock
        se_write(OP_Lock, 2 | (slot_num << 2), (crc[1] << 8) | crc[0], NULL, 0);

        return se_read1();
    }

    return 0;
}

static int se_lock_config_zone(const uint8_t config[128]) {
    uint8_t crc[2] = {0, 0};

    se_crc16_chain(128, config, crc);

    // do the lock: mode=0
    se_write(OP_Lock, 0x0, (crc[1] << 8) | crc[0], NULL, 0);

    return se_read1();
}

static int se_lock_data_zone(void) {
    // do the lock: mode=1 (datazone) + 0x80 (no CRC check)
    se_write(OP_Lock, 0x81, 0x0000, NULL, 0);

    return se_read1();
}

static int se_config_write(uint8_t* config) {
    // send all 128 bytes, less some that can't be written.
    for (int n = 16; n < 128; n += 4) {
        int rc;

        if (n == 84) continue;  // that word not writable

        // Must work on words, since can't write to most of the complete blocks.
        //  args = write_params(block=n//32, offset=n//4, is_config=True)
        //  p2 = (block << 3) | offset
        se_write(OP_Write, 0, n / 4, &config[n], 4);

        rc = se_read1();
        if (rc < 0) return -1;
    }

    return 0;
}

// One-time config and lockdown of the chip
//
// CONCERN: Must not be possible to call this function after replacing
// the chip deployed originally. But key secrets would have been lost
// by then anyway... looks harmless, and regardless once the datazone
// is locked, none of this code will work... but:
//
// IMPORTANT: If they blocked the real chip, and provided a blank one for
// us to write the (existing) pairing secret into, they would see the pairing
// secret in cleartext. They could then restore original chip and access freely.
//
// PASSPORT NOTE: We can eliminate the above by having the factory bootloader
//                be different than the normal bootloader. The factory bootloader
//                will have the one-time setup code only, not the runtime code.
//                The normal bootloader will NOT have the one-time setup code,
//                but WILL have the main runtime code. So swapping in blank
//                SE would not trigger us to write the pairing secret in the clear.
//
int se_setup_config(rom_secrets_t* secrets) {
    uint8_t config[128] = {0};
    int     rc          = se_config_read(config);
    if (rc < 0) return -1;

    uint8_t serial[9];
    memcpy(serial, &config[0], 4);
    memcpy(&serial[4], &config[8], 5);

    memcpy(secrets->se_serial_number, serial, sizeof(serial));

    // Setup steps:
    // - write config zone data
    // - lock that
    // - write pairing secret (test it works)
    // - pick RNG value for words secret (and forget it)
    // - set all PIN values to known value (zeros)
    // - set all money secrets to knonw value (zeros)
    // - lock the data zone
    if (config[87] == 0x55) {
        // config is still unlocked

        // setup "config zone" area of the chip
        static const uint8_t config_1[] = SE_CHIP_CONFIG_1;
        static const uint8_t config_2[] = SE_CHIP_CONFIG_2;

        memcpy(&config[16], config_1, sizeof(config_1));
        memcpy(&config[90], config_2, sizeof(config_2));

        // write it.
        if (se_config_write(config)) return -2;

        // lock config zone
        if (se_lock_config_zone(config)) return -3;

        // TODO: Add code to check that config was actually locked
    }

    if (config[86] == 0x55) {
        // data is still unlocked

        uint8_t zeros[72];
        memset(zeros, 0, sizeof(zeros));

        uint16_t unlocked = config[88] | (((uint8_t)config[89]) << 8);

        for (int kn = 0; kn < 16; kn++) {
            if (!(unlocked & (1 << kn))) continue;

            switch (kn) {
                case 12:
                    break;
                case 15:
                    break;

                case KEYNUM_pairing_secret:
                    if (se_write_data_slot(kn, secrets->pairing_secret, 32, false)) return -4;
                    break;

                case KEYNUM_pin_stretch:
                case KEYNUM_pin_attempt: {
                    // HMAC-SHA256 key (forgotten immediately), for:
                    // - phishing words
                    // - each pin attempt (limited by counter0)
                    // - stretching pin/words attempts (iterated may times)
                    // See mathcheck.py for details.
                    uint8_t tmp[32];

                    rng_buffer(tmp, sizeof(tmp));

                    if (se_write_data_slot(kn, tmp, 32, true)) return -5;
                } break;

                case KEYNUM_pin_hash:
                case KEYNUM_lastgood:
                case KEYNUM_firmware_timestamp:
                case KEYNUM_firmware_hash:
                    if (se_write_data_slot(kn, zeros, 32, false)) return -6;
                    break;

                case KEYNUM_supply_chain: {
                    // SCV key is in user settings flash
                    uint8_t* supply_chain_key = (uint8_t*)USER_SETTINGS_FLASH_ADDR;
                    bool     is_erased        = true;
                    for (uint32_t i = 0; i < 32; i++) {
                        if (supply_chain_key[i] != 0xFF) {
                            is_erased = false;
                        }
                    }

                    // If the scv key is not set in flash, then don't proceed, else validation will never work!
                    if (is_erased) {
                        return -11;
                    }

                    int rc = se_write_data_slot(kn, supply_chain_key, 32, false);

                    // Always erase the supply chain key, even if the write failed
                    flash_sector_erase(USER_SETTINGS_FLASH_ADDR);

                    if (rc) return -7;
                } break;

                case KEYNUM_seed:
                case KEYNUM_user_fw_pubkey:
                    if (se_write_data_slot(kn, zeros, 72, false)) return -8;
                    break;

                case KEYNUM_match_count: {
                    uint32_t buf[32 / 4] = {1024, 1024};
                    if (se_write_data_slot(KEYNUM_match_count, (uint8_t*)buf, sizeof(buf), false)) return -9;
                } break;

                case 0:
                    if (se_write_data_slot(kn, (uint8_t*)copyright_msg, 32, true)) return -10;
                    break;

                default:
                    break;
            }
        }

        // lock the data zone and effectively enter normal operation.
        if (se_lock_data_zone()) return -11;

        // TODO: Add code to check that data was actually locked
    }

    return 0;
}

// Do Info(p1=3) command, and return result.
//
// IMPORTANT: do not trust this result, could be MitM'ed.
//
uint8_t se_get_gpio(void) {
    int rc;
    se_write(OP_Info, 0x3, 0, NULL, 0);

    uint8_t tmp[4];
    rc = se_read(tmp, 4);
    if (rc < 0) return -1;

    return tmp[1];
}

int se_set_gpio(int state) {
    // 1=turn on green, 0=red light (if not yet configured to be secure)
    se_write(OP_Info, 3, 2 | (!!state), NULL, 0);

    // "Always return the current state in the first byte followed by three bytes of 0x00"
    // - simple 1/0, in LSB.
    uint8_t resp[4];
    int     rc = se_read(resp, 4);
    se_sleep();
    if (rc < 0) return -1;

    return ((resp[0] & 0x01) != state) ? -1 : 0;
}

// char buf[256];

// Set the GPIO using secure hash generated somehow already.
//
int se_set_gpio_secure(uint8_t* digest) {
    int rc;

    rc = se_pair_unlock();
    if (rc < 0) {
        // printf("se_pair_unlock failed: %d\r\n", rc);
        return -1;
    }

    rc = se_checkmac(KEYNUM_firmware_hash, digest);
    if (rc < 0) {
        return -1;
    }

    rc = se_set_gpio(1);
    if (rc < 0) {
        // printf("se_set_gpio(1) failed: %d\r\n", rc);
        return -1;
    }

    // printf("se_set_gpio_secure() NO ERROR!\r\n");
    return 0;
}

int se_program_board_hash(uint8_t* previous_hash, uint8_t* new_hash) {
#ifdef PRODUCTION_BUILD
    uint32_t attempts = 3;
    do {
        int rc = se_encrypted_write(KEYNUM_firmware_hash, KEYNUM_firmware_hash, previous_hash, new_hash, HASH_LEN);
        if (rc < 0) {
            printf("se_encrypted_write() ERROR: rc=%d\r\n", rc);
        }

        rc = se_pair_unlock();
        if (rc < 0) {
            printf("se_pair_unlock() failed in se_program_board_hash(): %d\r\n", rc);
            return -1;
        }

        rc = se_checkmac(KEYNUM_firmware_hash, new_hash);
        if (rc == 0) {
            return rc;
        }
        printf("se_checkmac() failed to verify...retrying\r\n");
        attempts--;
    } while (attempts > 0);
    printf("se_program_board_hash() ALL RETRIES FAILED\r\n");

    return -1;
#else
    return 0;
#endif /* PRODUCTION_BUILD */
}

bool se_valid_secret(uint8_t* secret) {
    int rc = se_checkmac(KEYNUM_pairing_secret, secret);
    if (rc < 0) return false;
    return true;
}
