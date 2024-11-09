// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
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
  0xff, 0xff, 0xff, 0x23, 	/*Color of index 1*/
  0xfe, 0xfe, 0xfe, 0x7b, 	/*Color of index 2*/
  0xfe, 0xfe, 0xfe, 0xf1, 	/*Color of index 3*/

  0x0b, 0xf4, 0x00, 
  0x2f, 0xfd, 0x00, 
  0x2f, 0x3d, 0x00, 
  0x1f, 0xfc, 0x00, 
  0x1f, 0xf4, 0x40, 
  0x2f, 0xfe, 0xd0, 
  0x3d, 0x7f, 0xe0, 
  0x3d, 0x6f, 0xd0, 
  0x2f, 0xff, 0xd0, 
  0x0b, 0xf5, 0x80, 
};

const lv_img_dsc_t ICON_INPUT_MODE_PUNCTUATION = {
  .header.cf = LV_IMG_CF_INDEXED_2BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 47,
  .data = ICON_INPUT_MODE_PUNCTUATION_map,
};
