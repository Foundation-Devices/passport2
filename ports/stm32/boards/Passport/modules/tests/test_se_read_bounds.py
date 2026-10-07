# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Compile secure-element response handling with a controlled transport."""

import os
import shlex
import subprocess
from pathlib import Path

from test_supply_chain_bounds import extract_between


BOARD_PARENT_INDEX = 2
BOARD = Path(__file__).resolve().parents[BOARD_PARENT_INDEX]


def test_se_response_copy_bounds(tmp_path):
    native = (BOARD / 'common/se.c').read_text()
    response_constants = '#define SE_RESPONSE_COUNT_SIZE' + extract_between(
        native, '#define SE_RESPONSE_COUNT_SIZE', '\n\n', 'se.c') + '\n'
    crc = 'void se_crc16_chain(' + extract_between(
        native, 'void se_crc16_chain(', '\n}\n', 'se.c') + '\n}\n'
    check = 'static bool check_crc(' + extract_between(
        native, 'static bool check_crc(', '\nvoid se_write(', 'se.c')
    read = 'int se_read(' + extract_between(
        native, 'int se_read(', '\nint se_read1(', 'se.c')
    source = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#define ERR(...) ((void)0)
#define ERRV(...) ((void)0)
#define OP_Info 0x30
#define IOFLAG_IDLE 0xbb
#define SE_COMMS_ERROR 0xee
#define SE_EX_RETRY_OUT 0xff
#define FRAMED_OPCODE 0
#define MIN_PAYLOAD_SIZE 1
#define MAX_PAYLOAD_SIZE 32
#define INFO_PAYLOAD_SIZE 4
#define STATUS_PAYLOAD_SIZE 1
#define GUARD_SIZE 1
#define GUARD_VALUE 0xa5
#define DEVICE_ERROR_CODE 0x08
#define READ_SUCCESS 0
#define READ_FAILURE (-1)
#define BYTE_COUNTER_RANGE (UINT8_MAX + 1)
''' + response_constants + r'''
#define MIN_RESPONSE_SIZE (STATUS_PAYLOAD_SIZE + SE_RESPONSE_OVERHEAD)
#define INFO_RESPONSE_SIZE (INFO_PAYLOAD_SIZE + SE_RESPONSE_OVERHEAD)
#define RESPONSE_BUFFER_SIZE (MAX_PAYLOAD_SIZE + SE_RESPONSE_OVERHEAD)
#define OUTPUT_BUFFER_SIZE (GUARD_SIZE + MAX_PAYLOAD_SIZE + GUARD_SIZE)
static const int opcodes[] = {FRAMED_OPCODE, OP_Info};
static int current_opcode, not_ready_n, short_error, len_error, len_error_two;
static int wdgtimeout, last_error, crc_errors, ln_retry, retry_out;
static int response_length;
static uint8_t response[RESPONSE_BUFFER_SIZE];
static int se_read_response(uint8_t* buffer, int capacity) {
    int copied = response_length < capacity ? response_length : capacity;
    memcpy(buffer, response, copied);
    return response_length;
}
static void _send_bits(int bits) { (void)bits; }
static void se_show_error(void) {}
''' + crc + check + read + r'''
static void prepare_response(int payload_length) {
    memset(response, 0, sizeof(response));
    response[0] = payload_length + SE_RESPONSE_OVERHEAD;
    for (int i = 0; i < payload_length; i++) response[i + SE_RESPONSE_COUNT_SIZE] = i + 1;
    se_crc16_chain(payload_length + SE_RESPONSE_COUNT_SIZE, response, response + payload_length + SE_RESPONSE_COUNT_SIZE);
}
int main(void) {
    uint8_t output[OUTPUT_BUFFER_SIZE];
    for (size_t opcode = 0; opcode < sizeof(opcodes) / sizeof(opcodes[0]); opcode++) {
        current_opcode = opcodes[opcode];
        for (int len = MIN_PAYLOAD_SIZE; len <= MAX_PAYLOAD_SIZE; len++) {
            prepare_response(len);
            response_length = len + SE_RESPONSE_OVERHEAD;
            memset(output, GUARD_VALUE, sizeof(output));
            assert(se_read(output + GUARD_SIZE, len) == READ_SUCCESS);
            assert(output[0] == GUARD_VALUE && output[len + GUARD_SIZE] == GUARD_VALUE);
            assert(memcmp(output + GUARD_SIZE, response + SE_RESPONSE_COUNT_SIZE, len) == 0);
        }
    }
    current_opcode = OP_Info;
    for (int actual = MIN_RESPONSE_SIZE; actual < INFO_RESPONSE_SIZE; actual++) {
        prepare_response(INFO_PAYLOAD_SIZE);
        response_length = actual;
        memset(output, GUARD_VALUE, sizeof(output));
        assert(se_read(output + GUARD_SIZE, INFO_PAYLOAD_SIZE) == READ_FAILURE);
        for (unsigned i = 0; i < sizeof(output); i++) assert(output[i] == GUARD_VALUE);
    }
    for (size_t opcode = 0; opcode < sizeof(opcodes) / sizeof(opcodes[0]); opcode++) {
        current_opcode = opcodes[opcode];
        prepare_response(INFO_PAYLOAD_SIZE);
        response_length = INFO_RESPONSE_SIZE + BYTE_COUNTER_RANGE;
        memset(output, GUARD_VALUE, sizeof(output));
        assert(se_read(output + GUARD_SIZE, INFO_PAYLOAD_SIZE) ==
               (current_opcode == OP_Info ? READ_SUCCESS : READ_FAILURE));
        assert(output[0] == GUARD_VALUE && output[GUARD_SIZE + INFO_PAYLOAD_SIZE] == GUARD_VALUE);
    }
    current_opcode = FRAMED_OPCODE;
    prepare_response(STATUS_PAYLOAD_SIZE);
    response[SE_RESPONSE_COUNT_SIZE] = DEVICE_ERROR_CODE;
    response_length = MIN_RESPONSE_SIZE;
    assert(se_read(output + GUARD_SIZE, MAX_PAYLOAD_SIZE) == READ_FAILURE);
    assert(last_error == DEVICE_ERROR_CODE);
    return 0;
}
'''
    test_source = tmp_path / 'se_read_bounds.c'
    test_source.write_text(source)
    executable = tmp_path / 'se_read_bounds'
    subprocess.run(shlex.split(os.environ.get('CC', 'cc')) +
                   ['-std=c99', '-Wall', '-Wextra', '-Werror', str(test_source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True)
