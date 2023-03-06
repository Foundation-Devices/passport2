// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// ui.c - Simple UI elements for the bootloader

#include <string.h>

#include "delay.h"
#include "display.h"
#include "gpio.h"
#include "passport_fonts.h"
#include "keypad-adp-5587.h"
#include "ui.h"
#include "utils.h"

#ifndef FACTORY_TEST

#include "utils.h"
#include "lvgl.h"
#include "images.h"

#define HEADER_HEIGHT 40
#define HEADER_TITLE_Y 18
#define SIDE_MARGIN 16
#define TOP_MARGIN 22

void ui_draw_image(uint16_t x, uint16_t y, const lv_img_dsc_t* image) {
    uint8_t mode = lv_cf_mode_to_draw_mode(image->header.cf);
    display_image(x, y, image->header.w, image->header.h, image->data, mode);
}

void ui_draw_header(char* title, uint16_t text_color) {
    // Title
    display_text(title, CENTER_X, HEADER_TITLE_Y, &FontTiny, text_color);
}

void ui_draw_image_button(uint16_t x, uint16_t y, const lv_img_dsc_t* image, bool is_pressed) {
    if (is_pressed) {
        y += 3;
    }

    ui_draw_image(x, y, image);
}

#define FOOTER_LEFT_BTN_X 16
#define FOOTER_RIGHT_BTN_X (SCREEN_WIDTH - 20 - 16)
#define FOOTER_BTN_Y (SCREEN_HEIGHT - 26)
#define PAGE_DOT_PADDING 6
#define PAGINATION_Y (SCREEN_HEIGHT - 12)

void ui_draw_footer(const lv_img_dsc_t* left_btn,
                    bool                is_left_pressed,
                    const lv_img_dsc_t* right_btn,
                    bool                is_right_pressed,
                    uint16_t            page_n,
                    uint16_t            of_m) {
    // Draw left button
    ui_draw_image_button(FOOTER_LEFT_BTN_X, FOOTER_BTN_Y, left_btn, is_left_pressed);

    // Draw right button
    ui_draw_image_button(FOOTER_RIGHT_BTN_X, FOOTER_BTN_Y, right_btn, is_right_pressed);

    if (of_m > 0) {
        uint16_t pagingation_width = (of_m * ICON_PAGE_DOT.header.w) + (of_m - 1) * PAGE_DOT_PADDING;
        uint16_t x                 = (SCREEN_WIDTH / 2) - (pagingation_width / 2);
        for (uint16_t n = 0; n < of_m; n++) {
            const lv_img_dsc_t* dot = (n == page_n) ? &ICON_PAGE_DOT_SELECTED : &ICON_PAGE_DOT;
            ui_draw_image(x, PAGINATION_Y, dot);
            x += ICON_PAGE_DOT.header.w + PAGE_DOT_PADDING;
        }
    }
}

uint16_t ui_draw_wrapped_text(uint16_t x, uint16_t y, uint16_t max_width, char* text, bool center) {
    // Buffer to hold each wrapped line
    char     line[80];
    uint16_t curr_y = y;

    while (*text != 0) {
        uint16_t sp              = 0;
        uint16_t last_space      = 0;
        uint16_t line_width      = 0;
        uint16_t first_non_space = 0;
        uint16_t text_len        = strlen(text);
        uint16_t sp_skip         = 0;

        // Skip leading spaces
        while (true) {
            if (text[sp] == ' ') {
                sp++;
                first_non_space = sp;
            } else if (text[sp] == '\n') {
                sp++;
                first_non_space = sp;
                curr_y += FontTiny.leading;
            } else {
                break;
            }
        }

        while (sp < text_len) {
            char ch = text[sp];
            if (ch == ' ') {
                last_space = sp;
            } else if (ch == '\n') {
                // Time to break the line - Skip over this character after copying and rendering the line with sp_skip
                sp_skip = 1;
                break;
            }

            uint16_t ch_width = display_get_char_width(ch, &FontTiny);
            line_width += ch_width;
            if (line_width >= max_width) {
                // If we found a space, we can break there, but if we didn't
                // then just break before we go over.
                if (last_space != 0) {
                    sp = last_space;
                }
                break;
            }
            sp++;
        }

        // Copy to prepare for rendering
        strncpy(line, text + first_non_space, sp - first_non_space);
        line[sp - first_non_space] = 0;
        text                       = text + sp + sp_skip;

        // Draw the line
        display_text(line, center ? CENTER_X : x, curr_y, &FontTiny, COLOR_TEXT_GREY);

        curr_y += FontTiny.leading;
    }

    return curr_y - y;
}

static bool poll_for_key(uint8_t* p_key, bool* p_is_key_down) {
    uint8_t key;

    if (!keypad_poll_key(&key)) {
        return false;
    }

    *p_key         = key & 0x7F;
    *p_is_key_down = (key & 0x80) ? true : false;

    return true;
}

KEY_ID STD_KEYS[]  = {KEY_LEFT_SELECT, KEY_RIGHT_SELECT};
KEY_ID PAGE_KEYS[] = {KEY_LEFT_SELECT, KEY_RIGHT_SELECT, KEY_LEFT, KEY_RIGHT};

KEY_ID ui_show_error(char*               screen_title,
                     char*               card_title,
                     char*               message,
                     const lv_img_dsc_t* left_btn,
                     const lv_img_dsc_t* right_btn,
                     bool                center) {
    return ui_show_message_color(screen_title, card_title, message, &LARGE_ICON_ERROR, left_btn, right_btn, center,
                                 COLOR_WHITE, 0, 0, STD_KEYS, 2);
}

KEY_ID ui_show_info(char*               screen_title,
                    char*               card_title,
                    char*               message,
                    const lv_img_dsc_t* left_btn,
                    const lv_img_dsc_t* right_btn,
                    bool                center) {
    return ui_show_message_color(screen_title, card_title, message, &LARGE_ICON_INFO, left_btn, right_btn, center,
                                 COLOR_WHITE, 0, 0, STD_KEYS, 2);
}

KEY_ID ui_show_question(char* screen_title, char* card_title, char* message, bool center) {
    return ui_show_message_color(screen_title, card_title, message, &LARGE_ICON_QUESTION, &ICON_CANCEL, &ICON_CHECKMARK,
                                 center, COLOR_WHITE, 0, 0, STD_KEYS, 2);
}

KEY_ID ui_show_missing_microsd(char*               screen_title,
                               char*               card_title,
                               char*               message,
                               const lv_img_dsc_t* left_btn,
                               const lv_img_dsc_t* right_btn,
                               bool                center) {
    return ui_show_message_color(screen_title, card_title, message, &LARGE_ICON_MICROSD, left_btn, right_btn, center,
                                 COLOR_WHITE, 0, 0, STD_KEYS, 2);
}

// Show message and then delay or wait for button press
KEY_ID ui_show_message(char*               screen_title,
                       char*               card_title,
                       char*               message,
                       const lv_img_dsc_t* left_btn,
                       const lv_img_dsc_t* right_btn,
                       bool                center) {
    return ui_show_message_color(screen_title, card_title, message, NULL, left_btn, right_btn, center, COLOR_WHITE, 0,
                                 0, STD_KEYS, 2);
}

KEY_ID ui_show_page(char*               screen_title,
                    char*               card_title,
                    char*               message,
                    const lv_img_dsc_t* icon,
                    const lv_img_dsc_t* left_btn,
                    const lv_img_dsc_t* right_btn,
                    bool                center,
                    uint16_t            page_n,
                    uint16_t            of_m) {
    return ui_show_message_color(screen_title, card_title, message, icon, left_btn, right_btn, center, COLOR_WHITE,
                                 page_n, of_m, PAGE_KEYS, 4);
}

bool key_is_enabled(KEY_ID key, KEY_ID enabled_keys[], uint8_t num_keys) {
    for (uint8_t i = 0; i < num_keys; i++) {
        if (enabled_keys[i] == key) {
            return true;
        }
    }
    return false;
}

// Show message and then delay or wait for button press
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
                             KEY_ID              enabled_keys[],
                             uint8_t             num_enabled_keys) {
    bool     exit             = false;
    KEY_ID   result           = KEY_0;
    bool     is_left_pressed  = false;
    bool     is_right_pressed = false;
    uint16_t max_width        = SCREEN_WIDTH - SIDE_MARGIN * 2;

    do {
        // Draw background image
        display_fill(COLOR_WHITE);
        ui_draw_image(0, 0, &BACKGROUND);

        // Draw header
        ui_draw_header(screen_title, header_text_color);

        uint16_t y = HEADER_HEIGHT + TOP_MARGIN;

        // Draw card title
        y += ui_draw_wrapped_text(0, y, max_width, card_title, true);

        // Draw icon if given
        if (icon != NULL) {
            y += 24;
            ui_draw_image(SCREEN_WIDTH / 2 - icon->header.w / 2, y, icon);
            y += icon->header.h + 16;
        } else {
            y += FontTiny.leading / 2;
        }

        // Draw text
        ui_draw_wrapped_text(SIDE_MARGIN, y, max_width, message, center);

        // Draw footer
        ui_draw_footer(left_btn, is_left_pressed, right_btn, is_right_pressed, page_n, of_m);

        display_show();

        // Only poll if we are not exiting
        if (!exit) {
            // Poll for key
            uint8_t key;
            bool    is_key_down;
            bool    key_read;
            do {
                key_read = poll_for_key(&key, &is_key_down);
            } while (!key_read);

            // Handle key
            if (key_read) {
                if (key_is_enabled(key, enabled_keys, num_enabled_keys)) {
                    if (is_key_down) {
                        switch (key) {
                            case KEY_RIGHT_SELECT:
                                is_right_pressed = true;
                                break;

                            case KEY_LEFT_SELECT:
                                is_left_pressed = true;
                                break;
                        }
                    } else {
                        switch (key) {
                            case KEY_RIGHT_SELECT:
                                is_right_pressed = false;
                                break;

                            case KEY_LEFT_SELECT:
                                is_left_pressed = false;
                                break;
                        }
                        // Getting here means the key is wanted
                        result = key;
                        exit   = true;
                        continue;
                    }
                } else {
                    delay_ms(50);
                }
            }
        }
    } while (!exit);

    // printf("result=%d\r\n", result);
    return result;
}

// Show the error message and give user the option to SHUTDOWN, or view
// CONTACT information. Then have option to go BACK to the error.
// NOTE: This function never returns!
void ui_show_fatal_error(char* error) {
    bool show_error = true;

    while (true) {
        if (show_error) {
            // Show the error
            if (ui_show_error("PASSPORT", "FATAL ERROR!", error, &ICON_SHUTDOWN, &ICON_EMAIL, true) ==
                KEY_RIGHT_SELECT) {
                show_error = false;
            } else {
                ui_ask_shutdown();
            }
        } else {
            // Show Contact Info
            ui_show_info("PASSPORT", "Contact Support", "Email support at:\n\nsupport@\nfoundationdevices.com",
                         &ICON_BACK, &ICON_CHECKMARK, true);
            show_error = true;
        }
    }
}

void ui_show_hex_buffer(char* card_title, uint8_t* data, uint32_t length) {
    char buf[512];
    bytes_to_hex_str(data, length, buf, 8, "\n");
    ui_show_message("HEX DUMP", card_title, buf, &ICON_SHUTDOWN, &ICON_FORWARD, true);
}

void ui_ask_shutdown() {
    if (ui_show_message("PASSPORT", "Shut down?", "\n\nAre you sure you\nwant to shut down?", &ICON_CANCEL,
                        &ICON_CHECKMARK, true) == KEY_RIGHT_SELECT) {
        display_clean_shutdown();
    }
}

#else

#define HEADER_HEIGHT 40
#define FOOTER_HEIGHT 32
#define SIDE_MARGIN 4
#define TOP_MARGIN 4

void ui_draw_header(char* title, uint16_t text_color, uint16_t bg_color) {
    uint16_t title_y = 10;

    // Background
    display_fill_rect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT, bg_color);

    // Title
    display_text(title, CENTER_X, title_y, &FontTiny, text_color);

    // Divider
    display_fill_rect(0, HEADER_HEIGHT - 4, SCREEN_WIDTH, 2, text_color);
}

void ui_draw_button(uint16_t x, uint16_t y, uint16_t w, uint16_t h, char* label, bool is_pressed) {
    if (is_pressed) {
        display_fill_rect(x, y, w, h, 1);
    } else {
        display_rect(x, y, w, h, 1);
    }

    // Measure text and center it in the button
    uint16_t label_width = display_measure_text(label, &FontTiny);

    x = x + (w / 2 - label_width / 2);
    y = y + (h / 2 - FontTiny.ascent / 2);

    display_text(label, x, y - 1, &FontTiny, is_pressed ? COLOR_WHITE : COLOR_BLACK);
}

void ui_draw_footer(char* left_btn, bool is_left_pressed, char* right_btn, bool is_right_pressed) {
    uint16_t btn_w = SCREEN_WIDTH / 2;

    // Draw left button
    ui_draw_button(-1, SCREEN_HEIGHT - FOOTER_HEIGHT + 1, btn_w + 1, FOOTER_HEIGHT, left_btn, is_left_pressed);

    // Draw right button
    ui_draw_button(btn_w - 1, SCREEN_HEIGHT - FOOTER_HEIGHT + 1, btn_w + 2, FOOTER_HEIGHT, right_btn, is_right_pressed);
}

void ui_draw_wrapped_text(uint16_t x, uint16_t y, uint16_t max_width, char* text, bool center) {
    // Buffer to hold each wrapped line
    char     line[80];
    uint16_t curr_y = y;

    while (*text != 0) {
        uint16_t sp              = 0;
        uint16_t last_space      = 0;
        uint16_t line_width      = 0;
        uint16_t first_non_space = 0;
        uint16_t text_len        = strlen(text);
        uint16_t sp_skip         = 0;

        // Skip leading spaces
        while (true) {
            if (text[sp] == ' ') {
                sp++;
                first_non_space = sp;
            } else if (text[sp] == '\n') {
                sp++;
                first_non_space = sp;
                curr_y += FontTiny.leading;
            } else {
                break;
            }
        }

        while (sp < text_len) {
            char ch = text[sp];
            if (ch == ' ') {
                last_space = sp;
            } else if (ch == '\n') {
                // Time to break the line - Skip over this character after copying and rendering the line with sp_skip
                sp_skip = 1;
                break;
            }

            uint16_t ch_width = display_get_char_width(ch, &FontTiny);
            line_width += ch_width;
            if (line_width >= max_width) {
                // If we found a space, we can break there, but if we didn't
                // then just break before we go over.
                if (last_space != 0) {
                    sp = last_space;
                }
                break;
            }
            sp++;
        }

        // Copy to prepare for rendering
        strncpy(line, text + first_non_space, sp - first_non_space);
        line[sp - first_non_space] = 0;
        text                       = text + sp + sp_skip;

        // Draw the line
        display_text(line, center ? CENTER_X : SIDE_MARGIN, curr_y, &FontTiny, COLOR_BLACK);

        curr_y += FontTiny.leading;
    }
}

// Show message and then delay or wait for button press
bool ui_show_message(
    char* title, char* message, const lv_img_dsc_t* left_btn, const lv_img_dsc_t* right_btn, bool center) {
    return ui_show_message_color(title, message, left_btn, right_btn, center, COLOR_BLACK, COLOR_WHITE);
}

// Show message and then delay or wait for button press
bool ui_show_message_color(char*               title,
                           char*               message,
                           const lv_img_dsc_t* left_btn,
                           const lv_img_dsc_t* right_btn,
                           bool                center,
                           uint16_t            header_text_color,
                           uint16_t            header_bg_color) {
    bool exit             = false;
    bool result           = false;
    bool is_left_pressed  = false;
    bool is_right_pressed = false;

    do {
        display_fill(COLOR_WHITE);

        // Draw the text
        ui_draw_wrapped_text(SIDE_MARGIN, HEADER_HEIGHT + TOP_MARGIN, SCREEN_WIDTH - SIDE_MARGIN * 2, message, center);

        // Draw the header
        ui_draw_header(title, header_text_color, header_bg_color);

        // Draw the footer
        ui_draw_footer(left_btn, is_left_pressed, right_btn, is_right_pressed);
        display_show();

#ifdef DEBUG
        delay_ms(5000);
        result = true;
    } while (exit);
#else
        // Only poll if we are not exiting
        if (!exit) {
            // Poll for key
            uint8_t key;
            bool    is_key_down;
            bool    key_read;
            do {
                key_read = poll_for_key(&key, &is_key_down);
            } while (!key_read);

            // Handle key
            if (key_read) {
                if (is_key_down) {
                    switch (key) {
                        case KEY_RIGHT_SELECT:
                            is_right_pressed = true;
                            break;

                        case KEY_LEFT_SELECT:
                            is_left_pressed = true;
                            break;
                    }
                } else {
                    switch (key) {
                        case KEY_RIGHT_SELECT:
                            is_right_pressed = false;
                            exit             = true;
                            result           = true;
                            continue;

                        case KEY_LEFT_SELECT:
                            is_left_pressed = false;
                            exit            = true;
                            result          = false;
                            continue;
                    }
                }
            } else {
                delay_ms(50);
            }
        }
    } while (!exit);
#endif  // DEBUG

    return result;
}

// Show the error message and give user the option to SHUTDOWN, or view
// CONTACT information. Then have option to go BACK to the error.
// NOTE: This function never returns!
void ui_show_fatal_error(char* error) {
    bool show_error = true;

    while (true) {
        if (show_error) {
            // Show the error
            if (ui_show_message("Fatal Error", error, &ICON_EMAIL, &ICON_SHUTDOWN, true)) {
                display_clean_shutdown();
            } else {
                show_error = false;
            }
        } else {
            // Show Contact Info
            if (ui_show_message("Contact", "\nContact us at:\n\nsupport@foundationdevices.com", &ICON_BACK,
                                &ICON_SHUTDOWN, true)) {
                display_clean_shutdown();
            } else {
                show_error = true;
            }
        }
    }
}

void ui_show_hex_buffer(char* title, uint8_t* data, uint32_t length) {
    char buf[512];
    bytes_to_hex_str(data, length, buf, 8, "\n");
    ui_show_message(title, buf, &ICON_SHUTDOWN, &ICON_CHECKMARK, true);
}

#endif /* FACTORY_TEST */
