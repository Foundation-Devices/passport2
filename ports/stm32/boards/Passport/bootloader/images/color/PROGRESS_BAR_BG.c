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
#ifndef LV_ATTRIBUTE_IMG_PROGRESS_BAR_BG
#define LV_ATTRIBUTE_IMG_PROGRESS_BAR_BG
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_PROGRESS_BAR_BG uint8_t PROGRESS_BAR_BG_map[] = {
  0x80, 0x80, 0x80, 0xff, 	/*Color of index 0*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 1*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 2*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 3*/

  0x00, 
  0x00, 
  0x00, 
};

const lv_img_dsc_t PROGRESS_BAR_BG = {
  .header.cf = LV_IMG_CF_INDEXED_2BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 1,
  .header.h = 3,
  .data_size = 20,
  .data = PROGRESS_BAR_BG_map,
};
