# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise native firmware-state checks with controlled SE responses."""

import ast
import asyncio
from contextlib import nullcontext
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import sys
from types import SimpleNamespace

import pytest

from test_supply_chain_bounds import extract_between


BOARD = Path(__file__).resolve().parents[2]


def function(source, prefix):
    return prefix + extract_between(source, prefix, '\n}\n', 'native source') + '\n}\n'


def compile_and_run(tmp_path, source, production, extra_sources=()):
    harness = tmp_path / 'firmware_state.c'
    harness.write_text(source)
    binary = tmp_path / 'firmware_state'
    flags = ['-DPRODUCTION_BUILD'] if production else ['-Wno-unused-parameter']
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c99', '-Wall', '-Wextra', '-Werror', '-g'] + flags +
                   ['-I', str(BOARD / 'include'), str(harness)] +
                   [str(path) for path in extra_sources] + ['-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


@pytest.mark.parametrize('production', [True, False])
def test_timestamp_read_verification(tmp_path, production):
    native = (BOARD / 'common/se.c').read_text()
    names = ['int se_pick_nonce(', 'int se_gendig_slot(', 'bool se_is_correct_tempkey(',
             'int se_checkmac_hard(', 'uint32_t se_get_firmware_timestamp(']
    functions = '\n'.join(function(native, name) for name in names)

    timestamp = 1700000000
    block = timestamp.to_bytes(4, 'little') + bytes(28)
    serial = bytes.fromhex('0123456789abcdefee')
    # Independent SHA-256 fixtures for the existing Nonce/GenDig/MAC sequence.
    responses = []
    for sequence in range(32):
        nonce = hashlib.sha256(b'R' * 32 + bytes([sequence]) * 20 + b'\x16\x00\x00').digest()
        digest = hashlib.sha256(block + b'\x15\x02\x0b\x00\xee\x01\x23' + bytes(25) + nonce).digest()
        mac = hashlib.sha256(b'P' * 32 + digest + b'\x08\x41\x01' + bytes(12) + b'\xee' +
                             serial[4:8] + serial[:4]).digest()
        responses.append('{' + ', '.join(str(value) for value in mac) + '}')
    source = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "se.h"
#include "se-config.h"
#include "sha256.h"
#undef LV_REFRESH
#define LV_REFRESH() ((void)0)
static struct {
    uint8_t pairing_secret[32];
    uint8_t se_serial_number[9];
} secrets;
#define rom_secrets (&secrets)
enum failure { NONE, READ, UNLOCK, NONCE, GENDIG, MAC, INVALID_MAC, STALE_MAC };
static enum failure failure;
static uint8_t candidate[32], previous_mac[32];
static unsigned sequence, command, read_calls, unlock_calls, clear_calls;
static const uint32_t expected_timestamp = ''' + str(timestamp) + r''';
static const uint8_t mac_responses[32][32] = {
''' + ',\n'.join(responses) + r'''
};
void rng_buffer(uint8_t* out, size_t len) {
    sequence++;
    assert(sequence < 32);
    memset(out, sequence, len);
}
void se_write(seopcode_t op, uint8_t p1, uint16_t p2, uint8_t* data, uint8_t len) {
    command = op;
    if (op == OP_Nonce) {
        assert(p1 == 0 && p2 == 0 && len == 20);
        for (unsigned i = 0; i < len; i++) assert(data[i] == sequence);
    } else if (op == OP_GenDig) {
        assert(p1 == 2 && p2 == KEYNUM_firmware_timestamp && len == 0);
    } else {
        assert(op == OP_MAC && p1 == 0x41 && p2 == KEYNUM_pairing_secret && len == 0);
    }
}
int se_read(uint8_t* out, uint8_t len) {
    assert(len == 32);
    if (command == OP_Nonce) {
        if (failure == NONCE) return -1;
        memset(out, 'R', len);
    } else {
        assert(command == OP_MAC);
        if (failure == MAC) return -1;
        memcpy(out, failure == STALE_MAC ? previous_mac : mac_responses[sequence], len);
        if (failure == INVALID_MAC) out[0] ^= 1;
        if (failure == NONE) memcpy(previous_mac, out, len);
    }
    return 0;
}
int se_read1(void) { return failure == GENDIG ? -1 : 0; }
void se_sleep(void) {}
int se_pair_unlock(void) { unlock_calls++; return failure == UNLOCK ? -1 : 0; }
int se_encrypted_read(int slot, int keynum, const uint8_t* key, uint8_t* out, int len) {
    assert(slot == KEYNUM_firmware_timestamp && keynum == KEYNUM_firmware_hash);
    assert(key != NULL && len == 32);
    read_calls++;
    memcpy(out, candidate, len);
    return failure == READ ? -1 : 0;
}
static bool check_equal(const void* a, const void* b, int len) { return memcmp(a, b, len) == 0; }
void memzero(void* data, size_t len) {
    assert(len == 32);
    memset(data, 0, len);
    clear_calls++;
}
''' + functions + r'''
int main(void) {
    uint8_t board_hash[32] = {0};
    memset(secrets.pairing_secret, 'P', 32);
    const uint8_t serial[9] = {1, 0x23, 0x45, 0x67, 0x89, 0xab, 0xcd, 0xef, 0xee};
    memcpy(secrets.se_serial_number, serial, sizeof(serial));
    memcpy(candidate, &expected_timestamp, sizeof(expected_timestamp));
#ifdef PRODUCTION_BUILD
    assert(se_get_firmware_timestamp(board_hash) == expected_timestamp);
    assert(read_calls == 1 && unlock_calls == 1 && sequence == 1 && clear_calls == 1);
    assert(se_get_firmware_timestamp(board_hash) == expected_timestamp);
    assert(sequence == 2);

    candidate[0] ^= 1;
    assert(se_get_firmware_timestamp(board_hash) == 0);
    candidate[0] ^= 1;
    candidate[31] = 1;
    assert(se_get_firmware_timestamp(board_hash) == 0);
    candidate[31] = 0;

    for (enum failure f = READ; f <= STALE_MAC; f++) {
        failure = f;
        unsigned cleared_before = clear_calls;
        assert(se_get_firmware_timestamp(board_hash) == 0);
        assert(clear_calls == cleared_before + 1);
    }
    failure = NONE;
    assert(se_get_firmware_timestamp(board_hash) == expected_timestamp);
#else
    assert(se_get_firmware_timestamp(board_hash) == 0);
    assert(read_calls == 0 && unlock_calls == 0 && sequence == 0 && clear_calls == 0);
#endif
    return 0;
}
'''
    compile_and_run(tmp_path, source, production, [BOARD / 'common/sha256.c'])


@pytest.mark.parametrize('production', [True, False])
def test_update_timestamp_failure_handling(tmp_path, production):
    native = (BOARD / 'modpassport.c').read_text()
    helper = function(native, 'STATIC uint32_t get_minimum_firmware_timestamp(')
    source = r'''
#include <assert.h>
#include <setjmp.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define STATIC static
#define HASH_LEN 32
#define MP_ERROR_TEXT(x) (x)
static int mp_type_RuntimeError;
static jmp_buf error;
static uint32_t timestamp;
static void get_current_board_hash(uint8_t* out) { memset(out, 0x42, HASH_LEN); }
static uint32_t se_get_firmware_timestamp(uint8_t* hash) {
    for (unsigned i = 0; i < HASH_LEN; i++) assert(hash[i] == 0x42);
    return timestamp;
}
void mp_raise_msg(const void* type, const char* message) {
    assert(type == &mp_type_RuntimeError);
    assert(strcmp(message, "Unable to read firmware timestamp.") == 0);
    longjmp(error, 1);
}
''' + helper + r'''
int main(void) {
    timestamp = 1700000000;
    assert(get_minimum_firmware_timestamp() == timestamp);
    timestamp = 0;
    if (setjmp(error) == 0) {
        assert(get_minimum_firmware_timestamp() == 0);
#ifdef PRODUCTION_BUILD
        assert(false);
#endif
    } else {
#ifndef PRODUCTION_BUILD
        assert(false);
#endif
    }
    return 0;
}
'''
    compile_and_run(tmp_path, source, production)
    for name in ['STATIC mp_obj_t mod_passport_verify_update_header(',
                 'STATIC mp_obj_t mod_passport_verify_update_signatures(']:
        wrapper = function(native, name)
        assert wrapper.index('get_minimum_firmware_timestamp()') < wrapper.index('foundation_firmware_verify_')


def test_header_state_failure_is_recoverable(tmp_path, monkeypatch):
    source = ast.parse((BOARD / 'modules/flows/update_firmware_flow.py').read_text())
    flow_class = next(node for node in source.body if isinstance(node, ast.ClassDef))
    # show_firmware_details() only adds card handling around this step.
    method = next(node for node in flow_class.body if node.name == 'check_firmware_file')
    messages, results = [], []

    class ErrorPage:
        def __init__(self, text):
            messages.append(text)

        async def show(self):
            return True

    def verify_header(_):
        raise RuntimeError('Unable to read firmware timestamp.')

    header_size = 2048
    path = tmp_path / 'firmware.bin'
    path.write_bytes(bytes(header_size))
    flow = SimpleNamespace(update_file_path=str(path), set_result=results.append)
    monkeypatch.setitem(sys.modules, 'common', SimpleNamespace())
    namespace = {
        'CardSlot': nullcontext,
        'ErrorPage': ErrorPage,
        'FW_HEADER_SIZE': header_size,
        'FW_MAX_SIZE': header_size,
        'passport': SimpleNamespace(InvalidFirmwareUpdate=ValueError, verify_update_header=verify_header),
    }
    isolated = ast.Module(body=[method], type_ignores=[])
    exec(compile(isolated, 'update_firmware_flow.py', 'exec'), namespace)
    asyncio.run(namespace['check_firmware_file'](flow))
    assert results == [False]
    assert messages == ['Firmware update cannot continue.\n\nUnable to read firmware timestamp.']
    assert not hasattr(flow, 'update_header')


@pytest.mark.parametrize('production', [True, False])
def test_recovery_keeps_staged_update_until_installed(tmp_path, production):
    native = (BOARD / 'bootloader/update.c').read_text()
    hashing = function(native, 'static secresult calculate_spi_hash(')
    update = function(native, 'void update_firmware(void) {')
    source = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fwheader.h"
#include "secresult.h"
#include "firmware-classification.h"
#include "sha256.h"

#define HAL_OK 0
#define BODY_LEN 3000
#define BODY_READS 3  /* 1 KB reads */
typedef int HAL_StatusTypeDef;
typedef enum { KEY_LEFT_SELECT = 98, KEY_RIGHT_SELECT = 99 } KEY_ID;
typedef struct { int unused; } icon_t;
icon_t ICON_SHUTDOWN, ICON_CHECKMARK, ICON_RETRY, ICON_FORWARD, ICON_CANCEL;

/* SPI flash: the update-request page, then the header, then the image body. */
uint8_t spi[256 + FW_HEADER_SIZE + BODY_LEN];
uint8_t expected_digest[HASH_LEN];
int failed_body_reads, body_reads, se_failures, se_reads, signatures_checked, updates, cleared, errors;
int installed_firmware_valid;
KEY_ID answer;
const icon_t* last_left;
char last_error[128];
static uint8_t spi_hdr_hash[HASH_LEN];

HAL_StatusTypeDef spi_setup(void) { return HAL_OK; }
HAL_StatusTypeDef spi_read(uint32_t addr, uint32_t len, uint8_t* buf) {
    assert(addr + len <= sizeof(spi));
    if (addr >= 256 + FW_HEADER_SIZE) {
        body_reads++;
        if (failed_body_reads) {
            failed_body_reads--;
            return 1;
        }
    }
    memcpy(buf, spi + addr, len);
    return HAL_OK;
}
void calculate_spi_hdr_hash(passport_firmware_header_t* hdr, uint8_t* hash, uint8_t len) {
    (void)hdr;
    memset(hash, 0x33, len);
}
void calculate_update_hash(uint8_t* spi_hash, uint8_t spi_len, uint8_t* hash, uint8_t len) {
    (void)spi_hash;
    (void)spi_len;
    memset(hash, 0x55, len);
}
secresult verify_header(passport_firmware_header_t* hdr) {
    (void)hdr;
    return SEC_TRUE;
}
void get_current_board_hash(uint8_t* hash) { memset(hash, 0x11, HASH_LEN); }
/* Incomplete installed firmware means only the update in progress may be installed. */
secresult verify_current_firmware(bool process_led) {
    (void)process_led;
    return installed_firmware_valid ? SEC_TRUE : SEC_FALSE;
}
void hash_board(uint8_t* digest, uint8_t len, uint8_t* board, uint8_t board_len) {
    assert(len == HASH_LEN && board_len == HASH_LEN);
    for (int i = 0; i < HASH_LEN; i++) board[i] = digest[i] ^ 0xa5;
}
uint32_t se_get_firmware_timestamp(uint8_t* board_hash) {
    se_reads++;
    if (se_failures) {
        se_failures--;
        return 0;
    }
    for (int i = 0; i < HASH_LEN; i++) assert(board_hash[i] == (expected_digest[i] ^ 0xa5));
    return 1700000000;
}
secresult verify_signature(passport_firmware_header_t* hdr, uint8_t* hash, uint32_t len) {
    (void)hdr;
    assert(len == HASH_LEN && memcmp(hash, expected_digest, HASH_LEN) == 0);
    signatures_checked++;
    return SEC_TRUE;
}
int se_program_board_hash(uint8_t* previous, uint8_t* next) {
    (void)previous;
    (void)next;
    abort();
}
int se_set_firmware_timestamp(uint8_t* board_hash, uint32_t timestamp) {
    (void)board_hash;
    (void)timestamp;
    abort();
}
static int do_update(uint32_t size) {
    assert(size == FW_HEADER_SIZE + BODY_LEN);
    assert(signatures_checked == 1 && cleared == 0);
    updates++;
    return 0;
}
/* The staged update only goes once it's installed, or when the user cancels it. */
void clear_update_from_spi_flash(uint32_t total_size) {
    (void)total_size;
    assert(updates == 1 || answer == KEY_LEFT_SELECT);
    cleared++;
}
KEY_ID ui_show_error(const char* title, const char* card, const char* message, const icon_t* left,
                     const icon_t* right, bool center) {
    (void)title;
    (void)card;
    (void)center;
    /* Nothing is checked, copied or cleared before the user answers. */
    assert(signatures_checked == 0 && updates == 0 && cleared == 0);
    assert(right == &ICON_RETRY);
    last_left = left;
    snprintf(last_error, sizeof(last_error), "%s", message);
    errors++;
    return answer;
}
KEY_ID ui_show_message(const char* title, const char* card, const char* message, const icon_t* left,
                       const icon_t* right, bool center) {
    (void)title;
    (void)card;
    (void)message;
    (void)left;
    (void)right;
    (void)center;
    abort();
}
void ui_ask_shutdown(void) { abort(); }
void passport_reset(void) { abort(); }

""" + hashing + update + r"""
static void stage(void) {
    failed_body_reads = body_reads = se_failures = se_reads = 0;
    signatures_checked = updates = cleared = errors = 0;
    installed_firmware_valid = 0;
    answer = KEY_RIGHT_SELECT;
    last_left = NULL;
    memset(spi, 0x55, HASH_LEN);
    passport_firmware_header_t hdr;
    memset(&hdr, 0x7e, sizeof(hdr));
    hdr.info.fwlength = BODY_LEN;
    hdr.signature.pubkey1 = 0;
    memcpy(spi + 256, &hdr, sizeof(hdr));
    for (int i = 0; i < BODY_LEN; i++) spi[256 + FW_HEADER_SIZE + i] = (uint8_t)(i * 7);

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, (uint8_t*)&hdr.info, sizeof(fw_info_t));
    sha256_update(&ctx, spi + 256 + FW_HEADER_SIZE, BODY_LEN);
    sha256_final(&ctx, expected_digest);
    sha256_init(&ctx);
    sha256_update(&ctx, expected_digest, HASH_LEN);
    sha256_final(&ctx, expected_digest);
}

int main(void) {
    /* A temporary SE error, then the same image is confirmed on retry and installed. */
    stage();
    se_failures = 1;
    update_firmware();
    assert(updates == 1 && cleared == 1 && signatures_checked == 1);
    assert(body_reads == BODY_READS);
#ifdef PRODUCTION_BUILD
    assert(se_reads == 2 && errors == 1);
    assert(strstr(last_error, "update in progress"));
#else
    assert(se_reads == 0 && errors == 0);
#endif

    /* A failed read while hashing stops before anything is checked; the retry hashes the
       whole image again, and that one digest serves both checks. */
    stage();
    failed_body_reads = 1;
    update_firmware();
    assert(errors == 1 && strstr(last_error, "Unable to read") && last_left == &ICON_SHUTDOWN);
    assert(updates == 1 && cleared == 1 && signatures_checked == 1);
    assert(body_reads == 1 + BODY_READS);
#ifdef PRODUCTION_BUILD
    assert(se_reads == 1);
#endif

    /* With working firmware installed, an update that stays unreadable can be cancelled.
       The staged update is dropped without being checked or installed, and boot goes on. */
    stage();
    installed_firmware_valid = 1;
    failed_body_reads = 1000;
    answer = KEY_LEFT_SELECT;
    update_firmware();
    assert(errors == 1 && strstr(last_error, "Unable to read") && last_left == &ICON_CANCEL);
    assert(cleared == 1 && updates == 0 && signatures_checked == 0 && se_reads == 0);
    return 0;
}
"""
    compile_and_run(tmp_path, source, production, [BOARD / 'common/sha256.c'])
