// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// ui.h - Simple UI elements for the bootloader

#include <stdbool.h>
#include <stdint.h>

#include "lvgl.h"

// #define PCB_VERSION 1
#if PCB_VERSION == 1
typedef enum {
    KEY_LEFT_SELECT  = 113,
    KEY_RIGHT_SELECT = 99,
    KEY_UP           = 104,
    KEY_DOWN         = 101,
    KEY_LEFT         = 102,
    KEY_RIGHT        = 100,
    KEY_1            = 112,
    KEY_2            = 103,
    KEY_3            = 111,
    KEY_4            = 114,
    KEY_5            = 109,
    KEY_6            = 110,
    KEY_7            = 107,
    KEY_8            = 108,
    KEY_9            = 106,
    KEY_0            = 97,
    KEY_POUND        = 105,
    KEY_STAR         = 98
} KEY_ID;
#else
typedef enum {
    KEY_LEFT_SELECT  = 112,
    KEY_RIGHT_SELECT = 103,
    KEY_UP           = 97,
    KEY_DOWN         = 105,
    KEY_LEFT         = 114,
    KEY_RIGHT        = 104,
    KEY_1            = 113,
    KEY_2            = 106,
    KEY_3            = 102,
    KEY_4            = 110,
    KEY_5            = 109,
    KEY_6            = 101,
    KEY_7            = 111,
    KEY_8            = 108,
    KEY_9            = 98,
    KEY_0            = 99,
    KEY_POUND        = 100,
    KEY_STAR         = 107
} KEY_ID;
#endif

#ifndef FACTORY_TEST
// UI elements
void     ui_draw_image(uint16_t x, uint16_t y, const lv_img_dsc_t* image);
void     ui_draw_header(char* title, uint16_t text_color);
void     ui_draw_footer(const lv_img_dsc_t* left_btn,
                        bool                is_left_pressed,
                        const lv_img_dsc_t* right_btn,
                        bool                is_right_pressed,
                        uint16_t            page_n,
                        uint16_t            of_m);
void     ui_draw_image_button(uint16_t x, uint16_t y, const lv_img_dsc_t* image, bool is_pressed);
uint16_t ui_draw_wrapped_text(uint16_t x, uint16_t y, uint16_t max_width, char* text, bool center);

KEY_ID ui_show_error(char*               screen_title,
                     char*               card_title,
                     char*               message,
                     const lv_img_dsc_t* left_btn,
                     const lv_img_dsc_t* right_btn,
                     bool                center);

KEY_ID ui_show_info(char*               screen_title,
                    char*               card_title,
                    char*               message,
                    const lv_img_dsc_t* left_btn,
                    const lv_img_dsc_t* right_btn,
                    bool                center);

KEY_ID ui_show_question(char* screen_title, char* card_title, char* message, bool center);

KEY_ID ui_show_missing_microsd(char*               screen_title,
                               char*               card_title,
                               char*               message,
                               const lv_img_dsc_t* left_btn,
                               const lv_img_dsc_t* right_btn,
                               bool                center);

KEY_ID ui_show_message(char*               screen_title,
                       char*               card_title,
                       char*               message,
                       const lv_img_dsc_t* left_btn,
                       const lv_img_dsc_t* right_btn,
                       bool                center);

KEY_ID ui_show_page(char*               screen_title,
                    char*               card_title,
                    char*               message,
                    const lv_img_dsc_t* icon,
                    const lv_img_dsc_t* left_btn,
                    const lv_img_dsc_t* right_btn,
                    bool                center,
                    uint16_t            page_n,
                    uint16_t            of_m);

bool key_is_enabled(KEY_ID key, KEY_ID enabled_keys[], uint8_t num_keys);

KEY_ID ui_show_message_color(char*               screen_title,
                             char*               card_title,
                             char*               message,
                             const lv_img_dsc_t* icon,
                             const lv_img_dsc_t* left_btn,
                             const lv_img_dsc_t* right_btn,
                             bool                center,
                             uint16_t            header_text_color,
                             uint16_t            page_n,
                             uint16_t            of_m,
                             uint8_t             enabled_keys[],
                             uint8_t             num_enabled_keys);

void ui_show_fatal_error(char* message);
void ui_show_hex_buffer(char* title, uint8_t* buf, uint32_t length);
void ui_background(const lv_img_dsc_t* bg_strip_left, const lv_img_dsc_t* bg_strip_right);
void ui_ask_shutdown();

#else

// UI elements
void ui_draw_header(char* title, uint16_t text_color, uint16_t bg_color);
void ui_draw_footer(char* left_btn, bool is_left_pressed, char* right_btn, bool is_right_pressed);
void ui_draw_button(uint16_t x, uint16_t y, uint16_t w, uint16_t h, char* label, bool is_pressed);
void ui_draw_wrapped_text(uint16_t x, uint16_t y, uint16_t max_width, char* text, bool center);
bool ui_show_message(char* title, char* message, char* left_btn, char* right_btn, bool center);
bool ui_show_message_color(char*    title,
                           char*    message,
                           char*    left_btn,
                           char*    right_btn,
                           bool     center,
                           uint16_t header_text_color,
                           uint16_t header_bg_color);
void ui_show_fatal_error(char* message);
void ui_show_hex_buffer(char* title, uint8_t* buf, uint32_t length);
void ui_background(const lv_img_dsc_t* bg_strip_left, const lv_img_dsc_t* bg_strip_right);
void ui_ask_shutdown();

#endif /* FACTORY_TEST */
