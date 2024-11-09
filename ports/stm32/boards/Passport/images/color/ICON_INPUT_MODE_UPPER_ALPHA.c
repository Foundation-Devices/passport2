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
#ifndef LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA
#define LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_UPPER_ALPHA uint8_t ICON_INPUT_MODE_UPPER_ALPHA_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0x2a, 	/*Color of index 1*/
  0xff, 0xff, 0xff, 0x87, 	/*Color of index 2*/
  0xfe, 0xfe, 0xfe, 0xf3, 	/*Color of index 3*/

  0x01, 0xf4, 0x00, 
  0x02, 0xf8, 0x00, 
  0x07, 0xfd, 0x00, 
  0x07, 0xae, 0x00, 
  0x0f, 0x5e, 0x00, 
  0x1f, 0x0f, 0x40, 
  0x2f, 0xff, 0x80, 
  0x7f, 0xff, 0xd0, 
  0xb8, 0x02, 0xe0, 
  0xf4, 0x01, 0xf0, 
};

const lv_img_dsc_t ICON_INPUT_MODE_UPPER_ALPHA = {
  .header.cf = LV_IMG_CF_INDEXED_2BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 47,
  .data = ICON_INPUT_MODE_UPPER_ALPHA_map,
};
