# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise native firmware-state checks with controlled SE responses."""

import hashlib
import os
from pathlib import Path
import shlex
import subprocess

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
