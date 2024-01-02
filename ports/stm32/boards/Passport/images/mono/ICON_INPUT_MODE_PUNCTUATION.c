// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifdef LV_LVGL_H_INCLUDE_SIMPLE
#include "lvgl.h"
#else
#include "lvgl/lvgl.h"
#endif

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif
#ifndef LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_PUNCTUATION
#define LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_PUNCTUATION
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_PUNCTUATION uint8_t ICON_INPUT_MODE_PUNCTUATION_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xfe, 0xfe, 0xfe, 0xb6, 	/*Color of index 1*/

  0x3e, 0x00, 
  0x7f, 0x00, 
  0x77, 0x00, 
  0x7e, 0x00, 
  0x7e, 0x80, 
  0x7f, 0xc0, 
  0x7f, 0xc0, 
  0x7f, 0xc0, 
  0x7f, 0xc0, 
  0x3f, 0x80, 
};

const lv_img_dsc_t ICON_INPUT_MODE_PUNCTUATION = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 29,
  .data = ICON_INPUT_MODE_PUNCTUATION_map,
};
