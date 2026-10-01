# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compile the actual provisioning function with deterministic public RNG samples."""

import os
import shlex
import subprocess
from pathlib import Path


BOARD = Path(__file__).resolve().parents[2]


def test_erased_first_word_is_resampled(tmp_path):
    flash = (BOARD / 'bootloader' / 'flash.c').read_text()
    function = flash.split('static void pick_pairing_secret(', 1)[1].split('\nsecresult flash_first_boot', 1)[0]
    source = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "secrets.h"

static uint32_t samples[64];
static unsigned cursor;
static uint32_t rng_sample(void) {
    assert(cursor < 64);
    return samples[cursor++];
}
''' + 'static void pick_pairing_secret(' + function + r'''
static uint32_t read_word(const uint8_t* p) {
    uint32_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}

static void check(uint32_t first, unsigned retries) {
    rom_secrets_t secrets;
    memset(&secrets, 0xaa, sizeof(secrets));
    for (unsigned i = 0; i < 64; i++) samples[i] = 0x12340000 + i;
    samples[0] = first;
    // The first retry also returns an erased word, forcing another retry.
    if (retries) samples[8] = 0xffffffff;
    cursor = 0;
    pick_pairing_secret(&secrets);
    assert(read_word(secrets.pairing_secret) == (retries ? samples[9] : first));
    for (unsigned i = 1; i < 8; i++) {
        assert(read_word(secrets.pairing_secret + 4*i) == samples[i]);
    }
    for (unsigned i = 0; i < sizeof(secrets.otp_key)/4; i++) {
        assert(read_word(secrets.otp_key + 4*i) == samples[8 + retries + i]);
    }
    for (unsigned i = 0; i < sizeof(secrets.hash_cache_secret)/4; i++) {
        assert(read_word(secrets.hash_cache_secret + 4*i) == samples[26 + retries + i]);
    }
    assert(cursor == 34 + retries);
    for (unsigned i = 0; i < sizeof(secrets.se_serial_number); i++) {
        assert(secrets.se_serial_number[i] == 0xaa);
    }
}

int main(void) {
    check(0xffffffff, 2);
    check(0x000000ff, 0);
    check(0x12345678, 0);
    return 0;
}
'''
    test_source = tmp_path / 'pairing.c'
    test_source.write_text(source)
    executable = tmp_path / 'pairing'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c99', '-Wall', '-Wextra', '-Wno-address-of-packed-member',
                    '-I', str(BOARD / 'include'), str(test_source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
