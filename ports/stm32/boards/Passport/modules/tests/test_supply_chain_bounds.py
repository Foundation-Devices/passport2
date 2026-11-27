# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compile actual native SCV entry points with instrumented hardware stand-ins."""

import os
import shlex
import subprocess
from pathlib import Path


BOARD = Path(__file__).resolve().parents[2]


def extract_between(source, start, end, filename):
    _, found_start, remainder = source.partition(start)
    assert found_start, '{}: missing harness start marker {!r}'.format(filename, start)
    extracted, found_end, _ = remainder.partition(end)
    assert found_end, '{}: missing harness end marker {!r} after {!r}'.format(filename, end, start)
    return extracted


def test_native_supply_chain_buffer_bounds(tmp_path):
    native = (BOARD / 'modpassport.c').read_text()
    functions = []
    for name in ['mod_passport_supply_chain_challenge', 'mod_passport_verify_supply_chain_server_signature']:
        prefix = 'STATIC mp_obj_t ' + name + '('
        functions.append(prefix + extract_between(
            native, prefix, '\nSTATIC MP_DEFINE_CONST_FUN_OBJ_2', 'modpassport.c'))
    dispatch = (BOARD / 'dispatch.c').read_text()
    case = extract_between(dispatch, 'case CMD_GET_SUPPLY_CHAIN_VALIDATION_WORDS:',
                           'case CMD_GET_RANDOM_BYTES:', 'dispatch.c')
    source = r'''
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define STATIC static
#define MP_BUFFER_READ 0
#define MP_BUFFER_WRITE 1
#define KEYNUM_supply_chain 1
#define mp_const_false ((void*)0)
#define mp_const_true ((void*)1)
typedef void* mp_obj_t;
typedef struct { void* buf; size_t len; } mp_buffer_info_t;
static int verify_calls, hmac_calls, unlock_calls, crypto_result;
static uint8_t supply_chain_validation_server_pubkey[64];
static void mp_get_buffer_raise(mp_obj_t obj, mp_buffer_info_t* info, int flags) {
    (void)flags;
    *info = *(mp_buffer_info_t*)obj;
}
static int se_pair_unlock(void) { unlock_calls++; return 0; }
static int se_hmac32(int slot, void* challenge, void* response) {
    (void)slot;
    hmac_calls++;
    memmove(response, challenge, 32);
    return 0;
}
static int uECC_secp256k1(void) { return 1; }
static int uECC_verify(void* key, void* hash, size_t len, void* sig, int curve) {
    (void)key; (void)hash; (void)sig; (void)curve;
    assert(len == 32);
    verify_calls++;
    return crypto_result;
}
static int supply_chain_validation_words(char* data, int len, uint32_t* result) {
    assert(len >= 32);
    return se_hmac32(1, data, result);
}
''' + '\n'.join(functions) + r'''
static int dispatch_words(uint8_t* buf_io, int len_in, uint32_t arg2) {
    int rv = 0;
    switch (1) { case 1:
''' + case + r'''
    }
    return rv;
}
int main(void) {
    uint8_t input[80] = {0}, output[80] = {0};
    mp_buffer_info_t hash = {input, 32}, signature = {output, 64};
    // Exercise both sides of each boundary, including zero-length buffers.
    size_t lengths[] = {0, 1, 16, 31, 32, 33, 63, 64, 65};
    for (unsigned i = 0; i < sizeof(lengths)/sizeof(lengths[0]); i++) {
        for (unsigned j = 0; j < sizeof(lengths)/sizeof(lengths[0]); j++) {
            hash.len = lengths[i]; signature.len = lengths[j];
            verify_calls = hmac_calls = unlock_calls = 0;
            crypto_result = 1;
            int valid_sig = hash.len == 32 && signature.len == 64;
            assert(mod_passport_verify_supply_chain_server_signature(&hash, &signature)
                   == (valid_sig ? mp_const_true : mp_const_false));
            assert(verify_calls == valid_sig);
            int valid_hmac = hash.len == 32 && signature.len >= 32;
            assert(mod_passport_supply_chain_challenge(&hash, &signature)
                   == (valid_hmac ? mp_const_true : mp_const_false));
            assert(hmac_calls == valid_hmac && unlock_calls == valid_hmac);
            hmac_calls = 0;
            int valid_dispatch = lengths[i] >= 32 && lengths[j] >= 32 && lengths[j] <= lengths[i];
            assert(dispatch_words(input, lengths[i], lengths[j]) == (valid_dispatch ? 0 : ERANGE));
            assert(hmac_calls == valid_dispatch);
        }
    }
    hmac_calls = 0;
    assert(dispatch_words(input, -1, 32) == ERANGE);
    assert(hmac_calls == 0);
    hash.len = 32; signature.len = 64; crypto_result = 0;
    assert(mod_passport_verify_supply_chain_server_signature(&hash, &signature) == mp_const_false);
    return 0;
}
'''
    test_source = tmp_path / 'supply_chain.c'
    test_source.write_text(source)
    executable = tmp_path / 'supply_chain'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c99', '-Wall', '-Wextra', '-Werror', str(test_source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
