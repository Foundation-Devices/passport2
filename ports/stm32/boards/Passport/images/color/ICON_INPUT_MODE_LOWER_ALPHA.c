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
#ifndef LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_LOWER_ALPHA
#define LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_LOWER_ALPHA
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_LOWER_ALPHA uint8_t ICON_INPUT_MODE_LOWER_ALPHA_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0x18, 	/*Color of index 1*/
  0xfe, 0xfe, 0xfe, 0x97, 	/*Color of index 2*/
  0xfe, 0xfe, 0xfe, 0xfd, 	/*Color of index 3*/

  0x00, 0x00, 0x00, 
  0x0f, 0xf9, 0x00, 
  0x0f, 0xfe, 0x00, 
  0x00, 0x1f, 0x00, 
  0x00, 0x0f, 0x00, 
  0x2f, 0xff, 0x00, 
  0x3f, 0xff, 0x00, 
  0x3c, 0x0f, 0x00, 
  0x3f, 0xff, 0x00, 
  0x2f, 0xff, 0x00, 
};

const lv_img_dsc_t ICON_INPUT_MODE_LOWER_ALPHA = {
  .header.cf = LV_IMG_CF_INDEXED_2BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 47,
  .data = ICON_INPUT_MODE_LOWER_ALPHA_map,
};
