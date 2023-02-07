// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Unix build for the simulator.

#include "py/obj.h"

#include "ring_buffer.h"

#include "../../../../lib/lv_bindings/driver/include/common.h"
#include "../../../../lib/lv_bindings/lv_conf.h"
#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

#ifndef KEYPAD_DEBUG
// #define KEYPAD_DEBUG 1
#endif

STATIC mp_obj_t key_cb = mp_const_none;
STATIC bool global_nav_keys_enabled = true;

STATIC bool is_global_key(uint32_t key)
{
    bool result = (key == LV_KEY_ESC || key == LV_KEY_ENTER) ||
                  (global_nav_keys_enabled && (key == LV_KEY_LEFT || key == LV_KEY_RIGHT));
    return result;
}

/// package: passport_lv

/// class Keypad:
///     """
///     Simulated keypad.
///     """
typedef struct _mp_obj_Keypad_t
{
    mp_obj_base_t base;
} mp_obj_Keypad_t;

/// def __init__(self):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_make_new(const mp_obj_type_t *type,
                                                size_t n_args,
                                                size_t n_kw,
                                                const mp_obj_t *args)
{
    mp_obj_Keypad_t *keypad = m_new_obj(mp_obj_Keypad_t);
    keypad->base.type = type;
    ring_buffer_init();
    return MP_OBJ_FROM_PTR(keypad);
}

/// def enqueue_keycode(self):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_enqueue_keycode(mp_obj_t self, mp_obj_t ch_obj, mp_obj_t is_pressed_obj)
{
    uint8_t ch = mp_obj_get_int(ch_obj);
    uint8_t is_pressed = mp_obj_get_int(is_pressed_obj);

    if (is_pressed)
    {
        ch |= 0x80;
    }
    ring_buffer_enqueue(ch);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_lv_Keypad_enqueue_keycode_obj, mod_passport_lv_Keypad_enqueue_keycode);

/// def get_keycode(self):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_get_keycode(mp_obj_t self)
{
    uint8_t buf = 0;
    if (ring_buffer_dequeue(&buf) == 0)
    {
        return mp_const_none;
    }
#if KEYPAD_DEBUG
    printf("[passport.Keypad] get_keycode(): %u\n", (unsigned)buf);
#endif // KEYPAD_DEBUG
    return mp_obj_new_int_from_uint(buf);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_lv_Keypad_get_keycode_obj, mod_passport_lv_Keypad_get_keycode);

STATIC void mod_passport_lv_Keypad_read_cb(lv_indev_drv_t *drv, lv_indev_data_t *data)
{
    uint8_t buf = 0;
    if (ring_buffer_dequeue(&buf) == 0)
    {
        return;
    }

#if KEYPAD_DEBUG
    printf("[passport.Keypad] read_cb(): buf=%02x\n", (unsigned)buf);
#endif // KEYPAD_DEBUG
    uint32_t key = data->key;
    switch (buf & 0x7F)
    {
    case '1':
        key = '1';
        break;
    case '2':
        key = '2';
        break;
    case '3':
        key = '3';
        break;
    case '4':
        key = '4';
        break;
    case '5':
        key = '5';
        break;
    case '6':
        key = '6';
        break;
    case '7':
        key = '7';
        break;
    case '8':
        key = '8';
        break;
    case '9':
        key = '9';
        break;
    case '0':
        key = '0';
        break;
    case 'u':
        key = LV_KEY_UP;
        break;
    case 'd':
        key = LV_KEY_DOWN;
        break;
    case 'l':
        key = LV_KEY_LEFT;
        break;
    case 'r':
        key = LV_KEY_RIGHT;
        break;
    case 'x':
        key = LV_KEY_ESC;
        break;
    case 'y':
        key = LV_KEY_ENTER;
        break;
    case '*':
        key = LV_KEY_BACKSPACE;
        break;
    case '#':
        key = '#';
        break;
    default:
        printf("UNKNOWN Key Code!");
    }

    bool is_pressed = (buf & 0x80) == 0x80;

    if (is_global_key(key))
    {
        mp_call_function_2(key_cb, MP_OBJ_NEW_SMALL_INT(key), is_pressed ? mp_const_true : mp_const_false);
        return;
    }

    data->key = key;
    data->state = is_pressed ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
    // printf("key=%d is_pressed=%s\n", key, is_pressed ? "true" : "false");
}
DEFINE_PTR_OBJ(mod_passport_lv_Keypad_read_cb);

/// def set_key_cb(self, key_cb):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_set_key_cb(mp_obj_t self_in, mp_obj_t key_cb_in)
{
    key_cb = key_cb_in;
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_lv_Keypad_set_key_cb_obj, mod_passport_lv_Keypad_set_key_cb);

/// def enable_global(self, enable):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_enable_global_nav_keys(mp_obj_t self_in, mp_obj_t enable)
{
    global_nav_keys_enabled = enable == mp_const_true ? true : false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_lv_Keypad_enable_global_nav_keys_obj,
                                 mod_passport_lv_Keypad_enable_global_nav_keys);

/// def inject(self, ch, is_pressed):
///     """
///     ch is one of: 0123456789udlrxy*#
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_inject(mp_obj_t self_in, mp_obj_t _ch, mp_obj_t _is_pressed)
{
    uint32_t ch = mp_obj_get_int(_ch);
    bool is_pressed = _is_pressed == mp_const_true ? true : false;
    uint8_t keycode;
    switch (ch)
    {
    case LV_KEY_UP:
        keycode = 'u';
        break;
    case LV_KEY_DOWN:
        keycode = 'd';
        break;
    case LV_KEY_LEFT:
        keycode = 'l';
        break;
    case LV_KEY_RIGHT:
        keycode = 'r';
        break;
    case LV_KEY_ESC:
        keycode = 'c';
        break;
    case LV_KEY_ENTER:
        keycode = 'y';
        break;
    case LV_KEY_BACKSPACE:
        keycode = '*';
        break;
    default:
        keycode = ch;
        break;
    }

    if (is_pressed)
    {
        keycode |= 0x80;
    }

    ring_buffer_enqueue(keycode);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_lv_Keypad_inject_obj, mod_passport_lv_Keypad_inject);

/// def __del__(self):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad___del__(mp_obj_t self)
{
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_lv_Keypad___del___obj, mod_passport_lv_Keypad___del__);

STATIC const mp_rom_map_elem_t mod_passport_lv_Keypad_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_Keypad)},
    {MP_ROM_QSTR(MP_QSTR_enqueue_keycode), MP_ROM_PTR(&mod_passport_lv_Keypad_enqueue_keycode_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_keycode), MP_ROM_PTR(&mod_passport_lv_Keypad_get_keycode_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_cb), MP_ROM_PTR(&PTR_OBJ(mod_passport_lv_Keypad_read_cb))},
    {MP_ROM_QSTR(MP_QSTR_set_key_cb), MP_ROM_PTR(&mod_passport_lv_Keypad_set_key_cb_obj)},
    {MP_ROM_QSTR(MP_QSTR_enable_global_nav_keys), MP_ROM_PTR(&mod_passport_lv_Keypad_enable_global_nav_keys_obj)},
    {MP_ROM_QSTR(MP_QSTR_inject), MP_ROM_PTR(&mod_passport_lv_Keypad_inject_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_passport_lv_Keypad___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_lv_Keypad_locals_dict, mod_passport_lv_Keypad_locals_dict_table);

const mp_obj_type_t mod_passport_lv_Keypad_type = {
    {&mp_type_type},
    .name = MP_QSTR_Keypad,
    .make_new = mod_passport_lv_Keypad_make_new,
    .locals_dict = (void *)&mod_passport_lv_Keypad_locals_dict,
};