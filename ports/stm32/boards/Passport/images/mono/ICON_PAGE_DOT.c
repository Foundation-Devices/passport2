// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
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
#ifndef LV_ATTRIBUTE_IMG_ICON_PAGE_DOT
#define LV_ATTRIBUTE_IMG_ICON_PAGE_DOT
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_PAGE_DOT uint8_t ICON_PAGE_DOT_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0xff, 	/*Color of index 1*/

  0x3c, 
  0x7e, 
  0xff, 
  0xff, 
  0xff, 
  0xff, 
  0x7e, 
  0x3c, 
};

const lv_img_dsc_t ICON_PAGE_DOT = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 8,
  .header.h = 8,
  .data_size = 17,
  .data = ICON_PAGE_DOT_map,
};
