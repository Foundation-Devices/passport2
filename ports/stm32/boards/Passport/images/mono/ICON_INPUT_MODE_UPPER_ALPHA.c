// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#if defined(LV_LVGL_H_INCLUDE_SIMPLE)
#include "lvgl.h"
#else
#include "lvgl/lvgl.h"
#endif


#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA
#define LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA uint8_t ICON_INPUT_MODE_UPPER_ALPHA_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xfe, 0xfe, 0xfe, 0xb7, 	/*Color of index 1*/

  0x1e, 0x00, 
  0x1e, 0x00, 
  0x3f, 0x00, 
  0x3f, 0x00, 
  0x3f, 0x00, 
  0x73, 0x80, 
  0x7f, 0x80, 
  0xff, 0xc0, 
  0xe1, 0xc0, 
  0xe1, 0xc0, 
};

const lv_img_dsc_t ICON_INPUT_MODE_UPPER_ALPHA = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 28,
  .data = ICON_INPUT_MODE_UPPER_ALPHA_map,
};
