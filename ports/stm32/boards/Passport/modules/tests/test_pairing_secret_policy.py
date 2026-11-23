# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Exercise future provisioning; deployed bootloaders are not field-upgradeable."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest


BOARD = Path(__file__).resolve().parents[2]


def extract_between(source, start, end, filename):
    _, found_start, remainder = source.partition(start)
    assert found_start, '{}: missing harness start marker {!r}'.format(filename, start)
    extracted, found_end, _ = remainder.partition(end)
    assert found_end, '{}: missing harness end marker {!r} after {!r}'.format(filename, end, start)
    return start + extracted


def compile_and_run(tmp_path, source):
    test_source = tmp_path / 'pairing.c'
    test_source.write_text(source)
    executable = tmp_path / 'pairing'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c99', '-Wall', '-Wextra', '-Werror', '-Wno-address-of-packed-member',
                    '-I', str(BOARD / 'include'), str(test_source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True, timeout=10)


@pytest.mark.parametrize('source, missing', [('end', 'start'), ('start', 'end')])
def test_extraction_reports_changed_boundaries(source, missing):
    with pytest.raises(AssertionError, match='flash.c: missing harness ' + missing + ' marker'):
        extract_between(source, 'start', 'end', 'flash.c')


def test_pairing_secret_provisioning(tmp_path):
    flash = (BOARD / 'bootloader' / 'flash.c').read_text()
    functions = extract_between(flash, '#define PAIRING_SECRET_MAX_RETRIES',
                                '\nsecresult flash_is_programmed', 'flash.c')
    source = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
#include "secrets.h"
#include "secresult.h"
#include "pprng.h"

#define WORDS(field) (sizeof(((rom_secrets_t*)0)->field) / sizeof(uint32_t))
#define SECRET_WORDS (WORDS(pairing_secret) + WORDS(otp_key) + WORDS(hash_cache_secret))
static uint32_t samples[SECRET_WORDS + 32];
static unsigned cursor, fail_at, configured, persisted, fatal_calls;
static rom_secrets_t saved, installed;
static jmp_buf failure;
#undef rom_secrets
#define rom_secrets (&installed)
#define HASH_LEN 32
#define FW_HEADER_SIZE 0
static struct { struct { unsigned fwlength, timestamp; } info; } firmware;
typedef __typeof__(firmware) passport_firmware_header_t;
#define FW_HDR (&firmware)
#define verify_header(header) ((void)(header), SEC_TRUE)
#define verify_signature(header, hash, len) ((void)(header), (void)(hash), (void)(len), SEC_TRUE)
#define hash_fw(info, ptr, len, out, size) \
    ((void)(info), (void)(ptr), (void)(len), memset(out, 0, size))
#define HAL_SuspendTick() ((void)0)
#define HAL_ResumeTick() ((void)0)
#define se_program_board_hash(a, b) ((void)(a), (void)(b), 0)
#define se_set_firmware_timestamp(a, b) ((void)(a), (void)(b), 0)

static bool is_pairing_secret_programmed(uint8_t* secret, unsigned len) {
    for (unsigned i = 0; i < len; i++) if (secret[i] != 0xff) return true;
    return false;
}
static int se_setup_config(rom_secrets_t* local) {
    configured++;
    saved = *local;
    return 0;
}
static int flash_bootloader(rom_secrets_t* local) {
    persisted++;
    assert(memcmp(local, &saved, sizeof(saved)) == 0);
    return 0;
}
void rng_fatal_error(void) {
    fatal_calls++;
    longjmp(failure, 1);
}
uint32_t rng_sample(void) {
    if (cursor == fail_at) rng_fatal_error();
    assert(cursor < sizeof(samples) / sizeof(samples[0]));
    return samples[cursor++];
}
''' + functions + r'''
static uint32_t read_word(const uint8_t* p) {
    uint32_t v;
    memcpy(&v, p, sizeof(v));
    return v;
}
static void reset(void) {
    for (unsigned i = 0; i < sizeof(samples) / sizeof(samples[0]); i++) samples[i] = 0x12340000 + i;
    memset(&installed, 0xff, sizeof(installed));
    memset(&saved, 0xaa, sizeof(saved));
    cursor = configured = persisted = fatal_calls = 0;
    fail_at = UINT32_MAX;
}
static void check(uint32_t first, unsigned retries) {
    reset();
    samples[0] = first;
    for (unsigned i = 0; i + 1 < retries; i++) samples[WORDS(pairing_secret) + i] = UINT32_MAX;
    assert(flash_first_boot() == SEC_TRUE);
    assert(configured == 1 && persisted == 1 && fatal_calls == 0);
    assert(read_word(saved.pairing_secret) == (retries ? samples[WORDS(pairing_secret) + retries - 1] : first));
    for (unsigned i = 1; i < WORDS(pairing_secret); i++) {
        assert(read_word(saved.pairing_secret + sizeof(uint32_t)*i) == samples[i]);
    }
    unsigned offset = WORDS(pairing_secret) + retries;
    for (unsigned i = 0; i < WORDS(otp_key); i++) {
        assert(read_word(saved.otp_key + sizeof(uint32_t)*i) == samples[offset + i]);
    }
    offset += WORDS(otp_key);
    for (unsigned i = 0; i < WORDS(hash_cache_secret); i++) {
        assert(read_word(saved.hash_cache_secret + sizeof(uint32_t)*i) == samples[offset + i]);
    }
    assert(cursor == SECRET_WORDS + retries);
    for (unsigned i = 0; i < sizeof(saved.se_serial_number); i++) assert(saved.se_serial_number[i] == 0);
}
static void expect_fatal(void) {
    if (setjmp(failure) == 0) {
        flash_first_boot();
        assert(!"Provisioning returned after entropy failure");
    }
    assert(fatal_calls == 1 && configured == 0 && persisted == 0);
}
int main(void) {
    check(0x000000ff, 0);
    check(0x12345678, 0);
    for (unsigned retry = 1; retry <= PAIRING_SECRET_MAX_RETRIES; retry++) check(UINT32_MAX, retry);
    reset();
    samples[0] = UINT32_MAX;
    for (unsigned i = 0; i < PAIRING_SECRET_MAX_RETRIES; i++) samples[WORDS(pairing_secret) + i] = UINT32_MAX;
    expect_fatal();
    assert(cursor == WORDS(pairing_secret) + PAIRING_SECRET_MAX_RETRIES);
    // Fail every sample position: pairing, resampling, OTP, and hash cache.
    for (unsigned i = 0; i < SECRET_WORDS; i++) {
        reset();
        fail_at = i;
        expect_fatal();
        assert(cursor == i);
    }
    reset();
    samples[0] = UINT32_MAX;
    fail_at = WORDS(pairing_secret);
    expect_fatal();
    return 0;
}
'''
    compile_and_run(tmp_path, source)


def test_rng_sample_has_bounded_hardware_failure(tmp_path):
    rng = (BOARD / 'common' / 'pprng.c').read_text()
    implementation = extract_between(rng, '#define RNG_MAX_POLL_ATTEMPTS', '\n// EOF', 'pprng.c')
    source = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <setjmp.h>
#include "pprng.h"
#define RNG_SR_DRDY 1U
#define RNG_SR_CEIS 2U
#define RNG_SR_SEIS 4U
#define RNG_SR_SECS 8U
#define RNG_CR_RNGEN 1U
#define __HAL_RCC_RNG_CLK_ENABLE() ((void)0)
#define MIN(a,b) ((a) < (b) ? (a) : (b))
static struct { volatile uint32_t CR, SR, DR; } hardware;
#define RNG (&hardware)
static jmp_buf failure;
static unsigned fatal_calls;
void rng_fatal_error(void) {
    fatal_calls++;
    longjmp(failure, 1);
}
''' + implementation + r'''
static void expect_fatal(uint32_t status, uint32_t data) {
    hardware.SR = status;
    hardware.DR = data;
    fatal_calls = 0;
    if (setjmp(failure) == 0) {
        rng_sample();
        assert(!"Unusable hardware RNG returned a sample");
    }
    assert(fatal_calls == 1);
}
int main(void) {
    hardware.SR = RNG_SR_DRDY;
    hardware.DR = 0x12345678;
    assert(rng_sample() == 0x12345678);
    expect_fatal(0, 0); // No data-ready indication.
    expect_fatal(RNG_SR_DRDY, 0x12345678); // Stuck duplicate.
    expect_fatal(RNG_SR_DRDY, 0); // Invalid zero output.
    expect_fatal(RNG_SR_SECS, 1); // Persistent seed error.
    return 0;
}
'''
    compile_and_run(tmp_path, source)
