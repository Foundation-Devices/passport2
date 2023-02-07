/*
 * SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef _SECURE_ELEMENT_H_
#define _SECURE_ELEMENT_H_

#include <stdbool.h>

// Status/Error Codes that occur in 4-byte groups. See page 50, table 9-3.
#define SE_COMMAND_OK 0x00
#define SE_CHECKMAC_FAIL 0x01
#define SE_PARSE_ERROR 0x03
#define SE_ECC_FAULT 0x05
#define SE_SELFTEST_ERROR 0x07
#define SE_EXEC_ERROR 0x0f
#define SE_AFTER_WAKE 0x11
#define SE_WATCHDOG_EXPIRE 0xEE
#define SE_COMM_ERROR 0xFF

#if 0
// break on any error: not helpful since some are normal
#define ERR(msg) BREAKPOINT;
#define ERRV(val, msg) BREAKPOINT;
#else
#define ERR(msg)
#define ERRV(val, msg)
#endif

// Opcodes from table 9-4, page 51
//
typedef enum {
    OP_CheckMac    = 0x28,
    OP_Counter     = 0x24,
    OP_DeriveKey   = 0x1C,
    OP_ECDH        = 0x43,
    OP_GenDig      = 0x15,
    OP_GenKey      = 0x40,
    OP_Info        = 0x30,
    OP_Lock        = 0x17,
    OP_MAC         = 0x08,
    OP_Nonce       = 0x16,
    OP_PrivWrite   = 0x46,
    OP_Random      = 0x1B,
    OP_Read        = 0x02,
    OP_Sign        = 0x41,
    OP_SHA         = 0x47,
    OP_UpdateExtra = 0x20,
    OP_Verify      = 0x45,
    OP_Write       = 0x12,
    OP_AES         = 0x51,
    OP_KDF         = 0x56,
    OP_SecureBoot  = 0x80,
    OP_SelfTest    = 0x77,
} seopcode_t;

extern const char* copyright_msg;

extern void     se_setup(void);
extern void     se_reset_chip(void);
extern void     se_keep_alive(void);
extern int      se_wake(void);
extern void     se_idle(void);
extern void     se_sleep(void);
extern void     se_crc16_chain(uint8_t length, const uint8_t* data, uint8_t crc[2]);
extern void     se_write(seopcode_t opcode, uint8_t p1, uint16_t p2, uint8_t* data, uint8_t data_len);
extern int      se_read(uint8_t* data, uint8_t len);
extern int      se_read1(void);
extern int      se_read_data_slot(int slot_num, uint8_t* data, int len);
extern int      se_config_read(uint8_t* config);
extern int      se_pair_unlock(void);
extern int      se_checkmac(uint8_t keynum, const uint8_t* secret);
extern int      se_checkmac_hard(uint8_t keynum, const uint8_t* secret);
extern int      se_gendig_slot(int slot_num, const uint8_t* slot_contents, uint8_t* digest);
extern bool     se_is_correct_tempkey(const uint8_t* expected_tempkey);
extern int      se_pick_nonce(uint8_t* num_in, uint8_t* tempkey);
extern int      se_encrypted_read(int data_slot, int read_kn, const uint8_t* read_key, uint8_t* data, int len);
extern int      se_encrypted_write(int data_slot, int write_kn, const uint8_t* write_key, const uint8_t* data, int len);
extern int      se_get_counter(uint32_t* result, uint8_t counter_number);
extern int      se_add_counter(uint32_t* result, uint8_t counter_number, int incr);
extern int      se_gendig_counter(int counter_num, const uint32_t expected_value, uint8_t digest[32]);
extern int      se_run_selftest(bool sha, bool aes, bool ecdh, bool ecdsa, bool rng);
extern int      se_set_firmware_timestamp(uint8_t* board_hash, uint32_t firmware_timestamp);
extern uint32_t se_get_firmware_timestamp(uint8_t* board_hash);

extern uint8_t se_show_error(void);

#ifndef PASSPORT_BOOTLOADER
#define LV_REFRESH() lv_refresh()
#else
#define LV_REFRESH()
#endif

#endif /* _SECURE_ELEMENT_H_ */
