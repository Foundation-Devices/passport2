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
#ifndef LV_ATTRIBUTE_IMG_ICON_PAGE_HOME
#define LV_ATTRIBUTE_IMG_ICON_PAGE_HOME
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_PAGE_HOME uint8_t ICON_PAGE_HOME_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0xff, 	/*Color of index 1*/

  0xff, 
  0xff, 
  0x00, 
  0xff, 
  0xff, 
  0x00, 
  0xff, 
  0xff, 
};

const lv_img_dsc_t ICON_PAGE_HOME = {
  .header.cf = LV_IMG_CF_INDEXED_1BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 8,
  .header.h = 8,
  .data_size = 17,
  .data = ICON_PAGE_HOME_map,
};
