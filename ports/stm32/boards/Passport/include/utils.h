/*
 * SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#ifndef _UTILS_H_
#define _UTILS_H_

#include <stdbool.h>
#include <stdint.h>
#include "fwheader.h"

#ifndef MIN
#define MIN(a, b) (((a) < (b)) ? (a) : (b))
#define MAX(a, b) (((a) > (b)) ? (a) : (b))
#endif
#define CLAMP(x, mn, mx) (((x) > (mx)) ? (mx) : (((x) < (mn)) ? (mn) : (x)))
#define SGN(x) (((x) < 0) ? -1 : (((x) > 0) ? 1 : 0))
#ifndef ABS
#define ABS(x) (((x) < 0) ? -(x) : (x))
#endif

#define LOCKUP_FOREVER() \
    while (1) {          \
        __WFI();         \
    }

extern bool lv_refresh_enabled;
extern void lv_refresh();

extern bool check_all_ones(void* ptrV, int len);
extern bool check_all_zeros(void* ptrV, int len);
extern bool check_equal(void* aV, void* bV, int len);
extern void xor_mixin(uint8_t* acc, uint8_t* more, int len);
extern void to_hex(char* buf, uint8_t value);
extern void bytes_to_hex_str(uint8_t* bytes, uint32_t len, char* str, uint32_t split_every, char* separator);

#ifndef PASSPORT_BOOTLOADER
extern void print_hex_buf(char* prefix, uint8_t* buf, int len);
#endif

extern void copy_bytes(uint8_t* src, int src_len, uint8_t* dest, int dest_len);

#ifdef PASSPORT_BOOTLOADER
uint8_t lv_cf_mode_to_draw_mode(uint32_t lv_mode);
#endif

void get_current_board_hash(uint8_t* hash_buf);

#ifndef PASSPORT_BOOTLOADER
#define MIN_SP 0x24074000
#define EOS_SENTINEL 0xDEADBEEF

void     set_stack_sentinel();
bool     check_stack_sentinel();
uint32_t getsp(void);
bool     check_stack(char* msg, bool print);

#endif


#define BRDREV0_PIN GPIO_PIN_13
#define BRDREV0_PORT GPIOD

#define BRDREV1_PIN GPIO_PIN_12
#define BRDREV1_PORT GPIOD

#define BRDREV2_PIN GPIO_PIN_11
#define BRDREV2_PORT GPIOD

typedef enum board_rev {
  REV_A = 0,
  REV_B = 1,
} board_rev_t;

board_rev_t get_board_rev(void);

#endif /* _UTILS_H_ */
