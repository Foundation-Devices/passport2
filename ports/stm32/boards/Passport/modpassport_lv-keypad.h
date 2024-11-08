// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "py/runtime.h"
#include "py/objstr.h"

#include "extint.h"
#include "pins.h"

#include "lib/lv_bindings/driver/include/common.h"
#include "lvgl/lvgl.h"

#include "keypad-adp-5587.h"
#include "ring_buffer.h"

extern ring_buffer_t                    keybuf;
const mp_obj_type_t                     mod_passport_lv_Keypad_type;
STATIC const mp_obj_fun_builtin_fixed_t mod_passport_lv_Keypad_irq_callback_obj;
STATIC mp_obj_t                         key_cb                  = mp_const_none;
STATIC bool                             global_nav_keys_enabled = true;
STATIC bool                             intercept_all_keys      = false;

typedef struct _key_filter_t {
    uint32_t release_time;
    bool     eat_next_release;
} key_filter_t;

typedef struct _keycode_map_t {
    uint8_t keycode;
    char    ch;
} keycode_map_t;

typedef struct _repeat_map_t {
    uint8_t ch;
    bool    repeat;
} repeat_map_t;

// #define PCB_VERSION 1
#if SCREEN_MODE_COLOR
#if PCB_VERSION == 1
STATIC keycode_map_t keycode_map[] = {
    {97, '0'},           {112, '1'},         {103, '2'},
    {111, '3'},          {114, '4'},         {109, '5'},
    {110, '6'},          {107, '7'},         {108, '8'},
    {106, '9'},          {104, LV_KEY_UP},  // up
    {101, LV_KEY_DOWN},                     // down
    {102, LV_KEY_LEFT},                     // left
    {100, LV_KEY_RIGHT},                    // right
    {113, LV_KEY_ESC},   {99, LV_KEY_ENTER}, {98, LV_KEY_BACKSPACE},
    {105, '#'},
};
#else
STATIC keycode_map_t keycode_map[] = {
    {99, '0'},           {113, '1'},          {106, '2'},
    {102, '3'},          {110, '4'},          {109, '5'},
    {101, '6'},          {111, '7'},          {108, '8'},
    {98, '9'},           {97, LV_KEY_UP},  // up
    {105, LV_KEY_DOWN},                    // down
    {114, LV_KEY_LEFT},                    // left
    {104, LV_KEY_RIGHT},                   // right
    {112, LV_KEY_ESC},   {103, LV_KEY_ENTER}, {107, LV_KEY_BACKSPACE},
    {100, '#'},
};
#endif
#else
STATIC keycode_map_t keycode_map[] = {
    {97, '0'},           {112, '1'},         {103, '2'},
    {111, '3'},          {114, '4'},         {109, '5'},
    {110, '6'},          {107, '7'},         {108, '8'},
    {106, '9'},          {104, LV_KEY_UP},  // up
    {101, LV_KEY_DOWN},                     // down
    {102, LV_KEY_LEFT},                     // left
    {100, LV_KEY_RIGHT},                    // right
    {113, LV_KEY_ESC},   {99, LV_KEY_ENTER}, {98, LV_KEY_BACKSPACE},
    {105, '#'},
};
#endif
#define KEYCODE_MAP_NUMOF (sizeof(keycode_map) / sizeof(keycode_map_t))

STATIC key_filter_t key_filter[KEYCODE_MAP_NUMOF];

STATIC repeat_map_t repeat_map[] = {
    {LV_KEY_UP, true},
    {LV_KEY_DOWN, true},
    {LV_KEY_BACKSPACE, true},
};

#define REPEAT_MAP_NUMOF (sizeof(repeat_map) / sizeof(repeat_map[0]))

// Convert from keycode to character (e.g., 0123456789udlrxy*#)
STATIC uint8_t keycode_to_char(uint8_t keycode, int8_t * key_index) {
    for (int i = 0; i < KEYCODE_MAP_NUMOF; i++) {
        if (keycode_map[i].keycode == keycode) {
            if (key_index) {
                *key_index = i;
            }
            return (uint8_t)keycode_map[i].ch;
        }
    }
    if (key_index) {
        *key_index = -1;
    }
    return 0;
}

// Convert from character (e.g., 0123456789udlrxy*#) to keycode
STATIC uint8_t char_to_keycode(uint8_t ch, bool is_pressed) {
    for (int i = 0; i < KEYCODE_MAP_NUMOF; i++) {
        if (keycode_map[i].ch == ch) {
            uint8_t keycode = (uint8_t)keycode_map[i].keycode;
            if (is_pressed) {
                keycode |= 0x80;
            }
            return keycode;
        }
    }

    return 0;
}

STATIC bool is_global_key(uint32_t key) {
    bool result = (key == LV_KEY_ESC || key == LV_KEY_ENTER) ||
                  (global_nav_keys_enabled && (key == LV_KEY_LEFT || key == LV_KEY_RIGHT));
    return result;
}

/// package: passport_lv

/// class Keypad:
///     """
///     """
typedef struct _mp_obj_Keypad_t {
    mp_obj_base_t base;
} mp_obj_Keypad_t;

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_make_new(const mp_obj_type_t* type,
                                                size_t               n_args,
                                                size_t               n_kw,
                                                const mp_obj_t*      args) {
    mp_obj_Keypad_t* keypad = m_new_obj(mp_obj_Keypad_t);
    keypad->base.type       = &mod_passport_lv_Keypad_type;

    keypad_init();

    return MP_OBJ_FROM_PTR(keypad);
}

/// def get_keycode(self) -> int:
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_get_keycode(mp_obj_t self) {
    uint8_t buf;

    // Try read from ring buffer first, then from keypad controller
    if (!ring_buffer_dequeue(&buf)) {
        if (!keypad_poll_key(&buf)) {
            return mp_const_none;
        }
    }

    uint8_t flag    = buf & 0x80;
    uint8_t keycode = buf & 0x7F;
    uint8_t ch      = keycode_to_char(keycode, NULL);
    if (ch == 0) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Unknown key read"));
    }

    buf = ch | flag;
    return mp_obj_new_int_from_uint(buf);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_lv_Keypad_get_keycode_obj, mod_passport_lv_Keypad_get_keycode);

/// def set_key_cb(self, key_cb):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_set_key_cb(mp_obj_t self_in, mp_obj_t key_cb_in) {
    key_cb = key_cb_in;
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_lv_Keypad_set_key_cb_obj, mod_passport_lv_Keypad_set_key_cb);

STATIC mp_obj_t mod_passport_lv_Keypad_set_key_repeat(mp_obj_t self_in, mp_obj_t _key, mp_obj_t _enabled){
    int8_t key = mp_obj_get_int(_key);
    bool enabled = mp_obj_is_true(_enabled);
    for (int i = 0; i < REPEAT_MAP_NUMOF; i++){
        if (repeat_map[i].ch == key) {
            repeat_map[i].repeat = enabled;
        }
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_lv_Keypad_set_key_repeat_obj, mod_passport_lv_Keypad_set_key_repeat);

/// def enable_global(self, enable):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_enable_global_nav_keys(mp_obj_t self_in, mp_obj_t enable) {
    global_nav_keys_enabled = enable == mp_const_true ? true : false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_lv_Keypad_enable_global_nav_keys_obj,
                                 mod_passport_lv_Keypad_enable_global_nav_keys);

/// def intercept_all(self, enable):
///     """
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_intercept_all(mp_obj_t self_in, mp_obj_t enable) {
    intercept_all_keys = enable == mp_const_true ? true : false;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_lv_Keypad_intercept_all_obj, mod_passport_lv_Keypad_intercept_all);

#define INITIAL_REPEAT_DELAY 250
#define REPEAT_DELAY 100

uint32_t        g_last_pressed_keycode = 0;
lv_indev_drv_t* g_drv                  = NULL;
lv_timer_t*     repeat_timer           = NULL;

STATIC void mod_passport_lv_Keypad_read_cb(lv_indev_drv_t* drv, lv_indev_data_t* data);
void        on_repeat(lv_timer_t* _timer);

void cancel_repeat_timer() {
    if (repeat_timer != NULL) {
        lv_timer_del(repeat_timer);
        repeat_timer = NULL;
        // printf("canceling repeat timer\r\n");
    }
}

void start_repeat_timer(uint32_t delay) {
    cancel_repeat_timer();

    repeat_timer = lv_timer_create(on_repeat, delay, NULL);
    // printf("starting repeat timer\r\n");
}

bool is_repeatable_key(uint32_t key) {
    for (int i = 0; i < REPEAT_MAP_NUMOF; i++) {
        if (repeat_map[i].ch == key) {
            return repeat_map[i].repeat;
        }
    }
    return false;
}

void on_repeat(lv_timer_t* _timer) {
    if (g_last_pressed_keycode != 0) {
        // printf(">>>>> on_repeat(): dispatching: %lu\r\n", g_last_pressed_keycode);
        // First send a release for the previous key to avoid confusing LVGL
        ring_buffer_enqueue(g_last_pressed_keycode & 0x7F);

        // Now send the repeat
        ring_buffer_enqueue(g_last_pressed_keycode);

        start_repeat_timer(REPEAT_DELAY);
    } else {
        cancel_repeat_timer();
    }
}

STATIC void mod_passport_lv_Keypad_read_cb(lv_indev_drv_t* drv, lv_indev_data_t* data) {
    g_drv = drv;

    uint8_t keycode;
    bool from_keypad = false;
    uint32_t key_time = 0;

    // Try read from ring buffer first, then from keypad controller
    if (!ring_buffer_dequeue(&keycode)) {
        if (!keypad_poll_key(&keycode)) {
            return;
        } else {
            //check to prevent accidental double taps, only if received from polling
            from_keypad = true;
            key_time = HAL_GetTick();
        }
    }

    int8_t   key_index  = -1;
    uint32_t key        = keycode_to_char(keycode & 0x7F, &key_index);
    bool     is_pressed = (keycode & 0x80) == 0x80;

    if (key_index == -1) {
        return;
    }

    if (from_keypad) {
        if (is_pressed && key_time - key_filter[key_index].release_time < 20) {
            key_filter[key_index].eat_next_release = true;
            return;
        }
        if (!is_pressed) {
            key_filter[key_index].release_time = key_time;
            if (key_filter[key_index].eat_next_release) {
                key_filter[key_index].eat_next_release = false;
                return;
            }
        }
    }

    // Remember this for repeat handling
    if (is_pressed && is_repeatable_key(key)) {
        // printf("\n----------------------------\r\n");
        start_repeat_timer(INITIAL_REPEAT_DELAY);
        g_last_pressed_keycode = keycode;
    } else {
        g_last_pressed_keycode = 0;
        cancel_repeat_timer();
    }

    if (is_global_key(key) || intercept_all_keys) {
        if (key_cb != mp_const_none) {
            mp_call_function_2(key_cb, MP_OBJ_NEW_SMALL_INT(key), is_pressed ? mp_const_true : mp_const_false);
        }
        return;
    }

    data->key   = key;
    data->state = is_pressed ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
    // printf("key=%lu is_pressed=%s\n", key, is_pressed ? "true" : "false");
}
DEFINE_PTR_OBJ(mod_passport_lv_Keypad_read_cb);

/// def inject(self, ch, is_pressed):
///     """
///     ch is one of: 0123456789udlrxy*#
///     """
STATIC mp_obj_t mod_passport_lv_Keypad_inject(mp_obj_t self_in, mp_obj_t _ch, mp_obj_t _is_pressed) {
    uint32_t ch         = mp_obj_get_int(_ch);
    bool     is_pressed = _is_pressed == mp_const_true ? true : false;
    uint8_t  keycode    = char_to_keycode(ch, is_pressed);
    ring_buffer_enqueue(keycode);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_lv_Keypad_inject_obj, mod_passport_lv_Keypad_inject);

STATIC const mp_rom_map_elem_t mod_passport_lv_Keypad_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_keycode), MP_ROM_PTR(&mod_passport_lv_Keypad_get_keycode_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_cb), MP_ROM_PTR(&PTR_OBJ(mod_passport_lv_Keypad_read_cb))},
    {MP_ROM_QSTR(MP_QSTR_set_key_cb), MP_ROM_PTR(&mod_passport_lv_Keypad_set_key_cb_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_key_repeat), MP_ROM_PTR(&mod_passport_lv_Keypad_set_key_repeat_obj)},
    {MP_ROM_QSTR(MP_QSTR_inject), MP_ROM_PTR(&mod_passport_lv_Keypad_inject_obj)},
    {MP_ROM_QSTR(MP_QSTR_enable_global_nav_keys), MP_ROM_PTR(&mod_passport_lv_Keypad_enable_global_nav_keys_obj)},
    {MP_ROM_QSTR(MP_QSTR_intercept_all), MP_ROM_PTR(&mod_passport_lv_Keypad_intercept_all_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_lv_Keypad_locals_dict, mod_passport_lv_Keypad_locals_dict_table);

const mp_obj_type_t mod_passport_lv_Keypad_type = {
    {&mp_type_type},
    .name        = MP_QSTR_Keypad,
    .make_new    = mod_passport_lv_Keypad_make_new,
    .locals_dict = (void*)&mod_passport_lv_Keypad_locals_dict,
};
