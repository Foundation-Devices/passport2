/*******************************************************************************
 * Size: 16 px
 * Bpp: 1
 * Opts:
 * This is the IBM Plex Medium font, renamed to "monospace" for ease of replacement
 ******************************************************************************/

#ifdef LV_LVGL_H_INCLUDE_SIMPLE
#include "lvgl.h"
#else
#include "lvgl/lvgl.h"
#endif

#ifndef LV_FONT_MONOSPACE_16_MONO
#define LV_FONT_MONOSPACE_16_MONO 1
#endif

#if LV_FONT_MONOSPACE_16_MONO

/*-----------------
 *    BITMAPS
 *----------------*/

/*Store the image of the glyphs*/
static LV_ATTRIBUTE_LARGE_CONST const uint8_t glyph_bitmap[] = {
    /* U+0020 " " */
    0x0,

    /* U+0030 "0" */
    0x3c, 0x66, 0xc2, 0xc3, 0xc3, 0xdb, 0xdb, 0xc3,
    0xc3, 0x43, 0x66, 0x3c,

    /* U+0031 "1" */
    0x1c, 0x1e, 0x1b, 0x19, 0x84, 0xc0, 0x60, 0x30,
    0x18, 0xc, 0x6, 0x3, 0xf, 0xf0,

    /* U+0032 "2" */
    0x78, 0xcc, 0xc6, 0x6, 0x6, 0xe, 0xc, 0x18,
    0x30, 0x60, 0xc0, 0xff,

    /* U+0033 "3" */
    0x3e, 0xe7, 0x43, 0x3, 0x6, 0x3c, 0x6, 0x3,
    0x3, 0x43, 0xc6, 0x7c,

    /* U+0034 "4" */
    0x7, 0x3, 0xc0, 0xb0, 0x6c, 0x13, 0xc, 0xc6,
    0x31, 0xc, 0xff, 0xc0, 0xc0, 0x30, 0xc,

    /* U+0035 "5" */
    0x7f, 0x40, 0x40, 0x40, 0x40, 0x5e, 0x67, 0x3,
    0x3, 0x43, 0xe6, 0x3c,

    /* U+0036 "6" */
    0x1c, 0x38, 0x30, 0x60, 0x60, 0xde, 0xe7, 0xc3,
    0xc3, 0xc3, 0x66, 0x3c,

    /* U+0037 "7" */
    0xff, 0xc2, 0xc6, 0x6, 0x4, 0xc, 0xc, 0x8,
    0x18, 0x18, 0x10, 0x30,

    /* U+0038 "8" */
    0x3c, 0xe7, 0xc3, 0xc3, 0x66, 0x3c, 0x66, 0xc3,
    0xc3, 0xc3, 0x66, 0x3c,

    /* U+0039 "9" */
    0x3c, 0x66, 0xc3, 0xc3, 0xc3, 0xe7, 0x7b, 0x6,
    0x6, 0xc, 0x1c, 0x38,

    /* U+0041 "A" */
    0x1c, 0xe, 0x7, 0x83, 0xc3, 0x61, 0x98, 0xcc,
    0x46, 0x7f, 0x30, 0xd8, 0x78, 0x30,

    /* U+0042 "B" */
    0xfc, 0xc6, 0xc6, 0xc6, 0xc6, 0xf8, 0xc6, 0xc3,
    0xc3, 0xc3, 0xc6, 0xfc,

    /* U+0043 "C" */
    0x3c, 0x66, 0x43, 0xc0, 0xc0, 0xc0, 0xc0, 0xc0,
    0xc0, 0x43, 0x66, 0x3c,

    /* U+0044 "D" */
    0xfc, 0xc6, 0xc2, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3,
    0xc3, 0xc2, 0xc6, 0xfc,

    /* U+0045 "E" */
    0xff, 0x83, 0x6, 0xc, 0x1f, 0xf0, 0x60, 0xc1,
    0x83, 0x7, 0xf0,

    /* U+0046 "F" */
    0xff, 0x83, 0x6, 0xc, 0x1f, 0xf0, 0x60, 0xc1,
    0x83, 0x6, 0x0,

    /* U+0047 "G" */
    0x3c, 0x66, 0x43, 0xc0, 0xc0, 0xc0, 0xcf, 0xc3,
    0xc3, 0xc3, 0x67, 0x3b,

    /* U+0048 "H" */
    0xc7, 0x8f, 0x1e, 0x3c, 0x7f, 0xf1, 0xe3, 0xc7,
    0x8f, 0x1e, 0x30,

    /* U+0049 "I" */
    0xfe, 0x30, 0x60, 0xc1, 0x83, 0x6, 0xc, 0x18,
    0x30, 0x67, 0xf0,

    /* U+004A "J" */
    0x7e, 0xc, 0x18, 0x30, 0x60, 0xc1, 0x83, 0x7,
    0x8f, 0x3b, 0xc0,

    /* U+004B "K" */
    0xc3, 0xc6, 0xcc, 0xcc, 0xd8, 0xf8, 0xf8, 0xec,
    0xcc, 0xc6, 0xc3, 0xc3,

    /* U+004C "L" */
    0xc1, 0x83, 0x6, 0xc, 0x18, 0x30, 0x60, 0xc1,
    0x83, 0x7, 0xf0,

    /* U+004D "M" */
    0xe7, 0xe7, 0xe7, 0xff, 0xdb, 0xdb, 0xdb, 0xd3,
    0xc3, 0xc3, 0xc3, 0xc3,

    /* U+004E "N" */
    0xe7, 0xcf, 0x9f, 0x3d, 0x7a, 0xf5, 0xeb, 0xcf,
    0x9f, 0x3e, 0x70,

    /* U+004F "O" */
    0x3c, 0x66, 0xc2, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3,
    0xc3, 0x43, 0x66, 0x3c,

    /* U+0050 "P" */
    0xfd, 0x8f, 0x1e, 0x3c, 0x78, 0xff, 0x60, 0xc1,
    0x83, 0x6, 0x0,

    /* U+0051 "Q" */
    0x3c, 0x66, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3,
    0xc3, 0x66, 0x7e, 0x18, 0x18, 0x1e,

    /* U+0052 "R" */
    0xfe, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3, 0xfe, 0xcc,
    0xcc, 0xc6, 0xc6, 0xc3,

    /* U+0053 "S" */
    0x3e, 0x63, 0xc0, 0xc0, 0xe0, 0x7e, 0x3f, 0x7,
    0x3, 0x3, 0xc6, 0x7c,

    /* U+0054 "T" */
    0xff, 0x8c, 0x6, 0x3, 0x1, 0x80, 0xc0, 0x60,
    0x30, 0x18, 0xc, 0x6, 0x3, 0x0,

    /* U+0055 "U" */
    0xc7, 0x8f, 0x1e, 0x3c, 0x78, 0xf1, 0xe3, 0xc7,
    0x8d, 0x93, 0xe0,

    /* U+0056 "V" */
    0x41, 0xb0, 0xd8, 0x6c, 0x62, 0x31, 0x98, 0xcc,
    0x64, 0x16, 0xf, 0x7, 0x3, 0x80,

    /* U+0057 "W" */
    0xc1, 0xe0, 0xf0, 0x7b, 0x3d, 0xd2, 0xa9, 0x54,
    0xaa, 0x75, 0x3a, 0x9d, 0xcc, 0xe0,

    /* U+0058 "X" */
    0x61, 0xb1, 0x8c, 0xc6, 0xc1, 0xe0, 0x60, 0x70,
    0x3c, 0x36, 0x19, 0x98, 0xc8, 0x30,

    /* U+0059 "Y" */
    0x61, 0x98, 0x63, 0x10, 0xcc, 0x12, 0x7, 0x80,
    0xe0, 0x30, 0xc, 0x3, 0x0, 0xc0, 0x30,

    /* U+005A "Z" */
    0xff, 0x3, 0x6, 0xe, 0xc, 0x18, 0x18, 0x30,
    0x70, 0x60, 0xc0, 0xff,

    /* U+0061 "a" */
    0x7c, 0xc6, 0x6, 0x6, 0x7e, 0xc6, 0xc6, 0xc6,
    0x7f,

    /* U+0062 "b" */
    0xc0, 0xc0, 0xc0, 0xc0, 0xdc, 0xe6, 0xc3, 0xc3,
    0xc3, 0xc3, 0xc3, 0xe6, 0xdc,

    /* U+0063 "c" */
    0x3c, 0xcf, 0x6, 0xc, 0x18, 0x30, 0x33, 0x3c,

    /* U+0064 "d" */
    0x3, 0x3, 0x3, 0x3, 0x3b, 0x67, 0xc3, 0xc3,
    0xc3, 0xc3, 0xc3, 0x67, 0x3b,

    /* U+0065 "e" */
    0x3c, 0x66, 0xc3, 0xc3, 0xff, 0xc0, 0xc2, 0x63,
    0x3e,

    /* U+0066 "f" */
    0xf, 0x18, 0x18, 0x18, 0xff, 0x18, 0x18, 0x18,
    0x18, 0x18, 0x18, 0x18, 0xfe,

    /* U+0067 "g" */
    0x7, 0x4, 0x7c, 0xc6, 0xc6, 0xc6, 0x3c, 0x40,
    0xc0, 0xc0, 0x7e, 0xc3, 0xc3, 0x7e,

    /* U+0068 "h" */
    0xc1, 0x83, 0x6, 0xd, 0xdc, 0xf1, 0xe3, 0xc7,
    0x8f, 0x1e, 0x3c, 0x60,

    /* U+0069 "i" */
    0x18, 0x30, 0x0, 0xf, 0x83, 0x6, 0xc, 0x18,
    0x30, 0x60, 0xcf, 0xe0,

    /* U+006A "j" */
    0x18, 0xc0, 0xf, 0x8c, 0x63, 0x18, 0xc6, 0x31,
    0x8c, 0x7e,

    /* U+006B "k" */
    0xc0, 0xc0, 0xc0, 0xc0, 0xc6, 0xcc, 0xd8, 0xf0,
    0xf8, 0xcc, 0xcc, 0xc6, 0xc3,

    /* U+006C "l" */
    0xf8, 0x30, 0x60, 0xc1, 0x83, 0x6, 0xc, 0x18,
    0x30, 0x60, 0xcf, 0xe0,

    /* U+006D "m" */
    0xff, 0xdb, 0xdb, 0xdb, 0xdb, 0xdb, 0xdb, 0xdb,
    0xdb,

    /* U+006E "n" */
    0xdd, 0xcf, 0x1e, 0x3c, 0x78, 0xf1, 0xe3, 0xc6,

    /* U+006F "o" */
    0x3c, 0x66, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3, 0x66,
    0x3c,

    /* U+0070 "p" */
    0xdc, 0xe6, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3, 0xe6,
    0xdc, 0xc0, 0xc0, 0xc0,

    /* U+0071 "q" */
    0x3b, 0x67, 0xc3, 0xc3, 0xc3, 0xc3, 0xc3, 0x67,
    0x3b, 0x3, 0x3, 0x3,

    /* U+0072 "r" */
    0xf7, 0x3f, 0x38, 0x30, 0x30, 0x30, 0x30, 0x30,
    0xfe,

    /* U+0073 "s" */
    0x7d, 0x8b, 0x7, 0x87, 0xc3, 0xc1, 0xe3, 0x7c,

    /* U+0074 "t" */
    0x30, 0x30, 0x30, 0xff, 0x30, 0x30, 0x30, 0x30,
    0x30, 0x30, 0x30, 0x1f,

    /* U+0075 "u" */
    0xc7, 0x8f, 0x1e, 0x3c, 0x78, 0xf1, 0xe3, 0x7e,

    /* U+0076 "v" */
    0xc3, 0xc2, 0x46, 0x66, 0x64, 0x2c, 0x3c, 0x38,
    0x18,

    /* U+0077 "w" */
    0xcc, 0xa6, 0x53, 0x2b, 0xb5, 0x5a, 0xbd, 0x4c,
    0xe6, 0x73, 0x0,

    /* U+0078 "x" */
    0xc2, 0x66, 0x2c, 0x38, 0x18, 0x3c, 0x6c, 0x66,
    0xc3,

    /* U+0079 "y" */
    0x41, 0xb1, 0x98, 0xc4, 0x43, 0x61, 0xb0, 0x50,
    0x38, 0x8, 0xc, 0x6, 0xe, 0x0,

    /* U+007A "z" */
    0xfe, 0xc, 0x30, 0xc3, 0x86, 0x18, 0x60, 0xfe
};


/*---------------------
 *  GLYPH DESCRIPTION
 *--------------------*/

static const lv_font_fmt_txt_glyph_dsc_t glyph_dsc[] = {
    {.bitmap_index = 0, .adv_w = 0, .box_w = 0, .box_h = 0, .ofs_x = 0, .ofs_y = 0} /* id = 0 reserved */,
    {.bitmap_index = 0, .adv_w = 154, .box_w = 1, .box_h = 1, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 1, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 13, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 27, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 39, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 51, .adv_w = 154, .box_w = 10, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 66, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 78, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 90, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 102, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 114, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 126, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 140, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 152, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 164, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 176, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 187, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 198, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 210, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 221, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 232, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 243, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 255, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 2, .ofs_y = 0},
    {.bitmap_index = 266, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 278, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 289, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 301, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 312, .adv_w = 154, .box_w = 8, .box_h = 14, .ofs_x = 1, .ofs_y = -2},
    {.bitmap_index = 326, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 338, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 350, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 364, .adv_w = 154, .box_w = 7, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 375, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 389, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 403, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 417, .adv_w = 154, .box_w = 10, .box_h = 12, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 432, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 444, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 453, .adv_w = 154, .box_w = 8, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 466, .adv_w = 154, .box_w = 7, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 474, .adv_w = 154, .box_w = 8, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 487, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 496, .adv_w = 154, .box_w = 8, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 509, .adv_w = 154, .box_w = 8, .box_h = 14, .ofs_x = 1, .ofs_y = -3},
    {.bitmap_index = 523, .adv_w = 154, .box_w = 7, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 535, .adv_w = 154, .box_w = 7, .box_h = 13, .ofs_x = 2, .ofs_y = 0},
    {.bitmap_index = 547, .adv_w = 154, .box_w = 5, .box_h = 16, .ofs_x = 2, .ofs_y = -3},
    {.bitmap_index = 557, .adv_w = 154, .box_w = 8, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 570, .adv_w = 154, .box_w = 7, .box_h = 13, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 582, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 591, .adv_w = 154, .box_w = 7, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 599, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 608, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = -3},
    {.bitmap_index = 620, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = -3},
    {.bitmap_index = 632, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 641, .adv_w = 154, .box_w = 7, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 649, .adv_w = 154, .box_w = 8, .box_h = 12, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 661, .adv_w = 154, .box_w = 7, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 669, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 678, .adv_w = 154, .box_w = 9, .box_h = 9, .ofs_x = 0, .ofs_y = 0},
    {.bitmap_index = 689, .adv_w = 154, .box_w = 8, .box_h = 9, .ofs_x = 1, .ofs_y = 0},
    {.bitmap_index = 698, .adv_w = 154, .box_w = 9, .box_h = 12, .ofs_x = 0, .ofs_y = -3},
    {.bitmap_index = 712, .adv_w = 154, .box_w = 7, .box_h = 9, .ofs_x = 1, .ofs_y = 0}
};

/*---------------------
 *  CHARACTER MAPPING
 *--------------------*/



/*Collect the unicode lists and glyph_id offsets*/
static const lv_font_fmt_txt_cmap_t cmaps[] =
{
    {
        .range_start = 32, .range_length = 1, .glyph_id_start = 1,
        .unicode_list = NULL, .glyph_id_ofs_list = NULL, .list_length = 0, .type = LV_FONT_FMT_TXT_CMAP_FORMAT0_TINY
    },
    {
        .range_start = 48, .range_length = 10, .glyph_id_start = 2,
        .unicode_list = NULL, .glyph_id_ofs_list = NULL, .list_length = 0, .type = LV_FONT_FMT_TXT_CMAP_FORMAT0_TINY
    },
    {
        .range_start = 65, .range_length = 26, .glyph_id_start = 12,
        .unicode_list = NULL, .glyph_id_ofs_list = NULL, .list_length = 0, .type = LV_FONT_FMT_TXT_CMAP_FORMAT0_TINY
    },
    {
        .range_start = 97, .range_length = 26, .glyph_id_start = 38,
        .unicode_list = NULL, .glyph_id_ofs_list = NULL, .list_length = 0, .type = LV_FONT_FMT_TXT_CMAP_FORMAT0_TINY
    }
};



/*--------------------
 *  ALL CUSTOM DATA
 *--------------------*/

#if LVGL_VERSION_MAJOR >= 8
/*Store all the custom data of the font*/
static  lv_font_fmt_txt_glyph_cache_t cache;
static const lv_font_fmt_txt_dsc_t font_dsc = {
#else
static lv_font_fmt_txt_dsc_t font_dsc = {
#endif
    .glyph_bitmap = glyph_bitmap,
    .glyph_dsc = glyph_dsc,
    .cmaps = cmaps,
    .kern_dsc = NULL,
    .kern_scale = 0,
    .cmap_num = 4,
    .bpp = 1,
    .kern_classes = 0,
    .bitmap_format = 0,
#if LVGL_VERSION_MAJOR >= 8
    .cache = &cache
#endif
};


/*-----------------
 *  PUBLIC FONT
 *----------------*/

/*Initialize a public general font descriptor*/
#if LVGL_VERSION_MAJOR >= 8
const lv_font_t lv_font_monospace_16_mono = {
#else
lv_font_t lv_font_monospace_16_mono = {
#endif
    .get_glyph_dsc = lv_font_get_glyph_dsc_fmt_txt,    /*Function pointer to get glyph's data*/
    .get_glyph_bitmap = lv_font_get_bitmap_fmt_txt,    /*Function pointer to get glyph's bitmap*/
    .line_height = 16,          /*The maximum line height required by the font*/
    .base_line = 3,             /*Baseline measured from the bottom of the line*/
#if !(LVGL_VERSION_MAJOR == 6 && LVGL_VERSION_MINOR == 0)
    .subpx = LV_FONT_SUBPX_NONE,
#endif
#if LV_VERSION_CHECK(7, 4, 0) || LVGL_VERSION_MAJOR >= 8
    .underline_position = -2,
    .underline_thickness = 1,
#endif
    .dsc = &font_dsc,          /*The custom font data. Will be accessed by `get_glyph_bitmap/dsc` */
    .fallback = NULL,
    .user_data = NULL
};



#endif /*#if LV_FONT_MONOSPACE_16_MONO*/

