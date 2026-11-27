# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Host tests: pytest ports/stm32/boards/Passport/modules/tests/test_bootloader_host.py."""

import os
from pathlib import Path
import shlex
import subprocess

BOARD = Path(__file__).resolve().parents[2]

HAL_STUB = '''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef enum { HAL_OK = 0, HAL_ERROR = 1 } HAL_StatusTypeDef;
'''


def build_and_run(tmp_path, name, source):
    harness = tmp_path / (name + '.c')
    harness.write_text(source)
    binary = tmp_path / name
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=gnu99', '-Wall', '-Werror', str(harness), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)


def test_scv_key_clear_is_confirmed_c(tmp_path):
    source = (BOARD / 'common/spiflash.c').read_text()
    key_helpers = source[source.index('#define SPI_ADDR_SCV_KEY'):]
    build_and_run(tmp_path, 'scv_clear', HAL_STUB + '''
static uint8_t flash[4096];
static int erase_errors, erases_ignored, read_errors, erase_calls;

HAL_StatusTypeDef spi_sector_erase(uint32_t addr) {
    assert(addr == 0);
    erase_calls++;
    if (erase_errors > 0) {
        erase_errors--;
        return HAL_ERROR;
    }
    if (erases_ignored > 0) {
        erases_ignored--;
        return HAL_OK;
    }
    memset(flash, 0xFF, sizeof(flash));
    return HAL_OK;
}

HAL_StatusTypeDef spi_read(uint32_t addr, int len, uint8_t* buf) {
    if (read_errors > 0) {
        read_errors--;
        return HAL_ERROR;
    }
    memcpy(buf, flash + addr, len);
    return HAL_OK;
}

HAL_StatusTypeDef spi_write(uint32_t addr, int len, const uint8_t* buf) {
    memcpy(flash + addr, buf, len);
    return HAL_OK;
}
''' + key_helpers + '''
static void stage_key(void) {
    uint8_t key[32];
    memset(flash, 0xFF, sizeof(flash));
    memset(key, 0xA5, sizeof(key));
    assert(spi_set_scv_key(key));
    erase_errors = erases_ignored = read_errors = erase_calls = 0;
}

int main(void) {
    stage_key();
    assert(spi_clear_scv_key());
    assert(erase_calls == 1);

    // An erase or read-back that fails is retried.
    stage_key();
    erase_errors = 2;
    assert(spi_clear_scv_key());
    assert(erase_calls == 3);

    stage_key();
    read_errors = 1;
    assert(spi_clear_scv_key());

    stage_key();
    erases_ignored = 2;
    assert(spi_clear_scv_key());

    // A key that can't be confirmed gone is reported, not assumed.
    stage_key();
    erases_ignored = 3;
    assert(!spi_clear_scv_key());

    stage_key();
    erase_errors = 3;
    assert(!spi_clear_scv_key());

    stage_key();
    read_errors = 3;
    assert(!spi_clear_scv_key());
    return 0;
}
''')


def test_scv_key_provisioning_c(tmp_path):
    source = (BOARD / 'bootloader/se-atecc608a.c').read_text()
    start = source.index('case KEYNUM_supply_chain: {')
    case = source[start:source.index('} break;', start) + len('} break;')]
    build_and_run(tmp_path, 'scv_provision', HAL_STUB + '''
#define KEYNUM_supply_chain 7

static uint8_t staged[32];
static bool read_ok, write_ok, clear_ok;
static int writes, clears, wipes;
static uint8_t written[32];
static void* write_buf;
static void* wiped_buf;
static size_t wiped_len;
static bool wiped_after_write;

HAL_StatusTypeDef spi_setup(void) {
    return HAL_OK;
}

bool spi_get_scv_key(uint8_t* buf) {
    memcpy(buf, staged, sizeof(staged));
    return read_ok;
}

bool spi_clear_scv_key(void) {
    clears++;
    return clear_ok;
}

int se_write_data_slot(int slot_num, uint8_t* data, int len, bool lock_it) {
    assert(slot_num == KEYNUM_supply_chain && len == 32 && !lock_it);
    writes++;
    write_buf = data;
    memcpy(written, data, sizeof(written));
    return write_ok ? 0 : 1;
}

void memzero(void* const pnt, const size_t len) {
    memset(pnt, 0, len);
    wipes++;
    wiped_buf = pnt;
    wiped_len = len;
    wiped_after_write = writes > 0;
}

static int provision(int kn) {
    switch (kn) {
''' + case + '''
    }
    return 0;
}

static void reset(uint8_t fill) {
    memset(staged, fill, sizeof(staged));
    read_ok = write_ok = clear_ok = true;
    writes = clears = wipes = 0;
    wiped_buf = write_buf = NULL;
    wiped_len = 0;
    wiped_after_write = false;
}

int main(void) {
    // The key goes to the SE, its stack copy is wiped, and SPI is cleared.
    reset(0x5A);
    assert(provision(KEYNUM_supply_chain) == 0);
    assert(writes == 1 && memcmp(written, staged, sizeof(staged)) == 0);
    assert(wipes == 1 && wiped_buf == write_buf && wiped_len == 32 && wiped_after_write);
    assert(clears == 1);

    // Setup does not finish while the key may still be in SPI flash.
    reset(0x5A);
    clear_ok = false;
    assert(provision(KEYNUM_supply_chain) != 0);
    assert(writes == 1 && wipes == 1 && clears == 1);

    // A failed SE write still wipes and clears the key.
    reset(0x5A);
    write_ok = false;
    assert(provision(KEYNUM_supply_chain) != 0);
    assert(wipes == 1 && clears == 1);

    // A failed read wipes whatever was read, and nothing is written.
    reset(0x5A);
    read_ok = false;
    assert(provision(KEYNUM_supply_chain) != 0);
    assert(writes == 0 && wipes == 1 && wiped_len == 32);

    // No key staged: nothing to write or clear.
    reset(0xFF);
    assert(provision(KEYNUM_supply_chain) != 0);
    assert(writes == 0 && clears == 0);
    return 0;
}
''')
