// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
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

#ifndef LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_NUMERIC
#define LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_NUMERIC
#endif

const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_ICON_INPUT_MODE_NUMERIC uint8_t ICON_INPUT_MODE_NUMERIC_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0xf9, 	/*Color of index 1*/

  0x1c, 0x00, 
  0x1c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
  0x0c, 0x00, 
};

const lv_img_dsc_t ICON_INPUT_MODE_NUMERIC = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 10,
  .header.h = 10,
  .data_size = 28,
  .data = ICON_INPUT_MODE_NUMERIC_map,
};
