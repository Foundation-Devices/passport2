// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#include "py/runtime.h"
#include "py/objstr.h"


#define LOG_BUFFER_SIZE 12288

char log_buffer[LOG_BUFFER_SIZE] = {0};  // Initialize buffer to all zeros
size_t log_position = 0;  // Current position in the buffer

void clear_log(void) {
    memset(log_buffer, 0, LOG_BUFFER_SIZE);  // Clear the buffer contents
    log_position = 0;  // Reset the buffer position
}

void write_to_log(const char *format, ...) {
    va_list args;
    va_start(args, format);

    // Check remaining space in the buffer
    int available_space = LOG_BUFFER_SIZE - log_position;
    if (available_space <= 0) {
        // clear_log();
        return;
    }

    // Use vsnprintf to append to the buffer
    int written = vsnprintf(log_buffer + log_position, available_space, format, args);
    if (written > 0) {
        log_position += written;
    }

    va_end(args);
}

STATIC mp_obj_t modlogging_get_log(void) {
    vstr_t vstr;
    size_t len = MIN(LOG_BUFFER_SIZE, log_position);
    vstr_init_len(&vstr, len);
    memcpy(vstr.buf, log_buffer, len);
    vstr.len = len;

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
MP_DEFINE_CONST_FUN_OBJ_0(modlogging_get_log_obj, modlogging_get_log);

// Top level

STATIC const mp_rom_map_elem_t mp_module_logging_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_log), MP_ROM_PTR(&modlogging_get_log_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_logging_globals, mp_module_logging_globals_table);

const mp_obj_module_t mp_module_logging = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mp_module_logging_globals,
};

MP_REGISTER_MODULE(MP_QSTR_logging, mp_module_logging, 1);
