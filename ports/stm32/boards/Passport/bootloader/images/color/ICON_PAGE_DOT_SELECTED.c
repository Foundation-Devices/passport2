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
#ifndef LV_ATTRIBUTE_IMG_ICON_PAGE_DOT_SELECTED
#define LV_ATTRIBUTE_IMG_ICON_PAGE_DOT_SELECTED
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_PAGE_DOT_SELECTED uint8_t ICON_PAGE_DOT_SELECTED_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xb8, 0x9c, 0x00, 0x7f, 	/*Color of index 1*/
  0xb9, 0x9d, 0x00, 0x80, 	/*Color of index 2*/
  0xb9, 0x9c, 0x00, 0x8f, 	/*Color of index 3*/
  0xb9, 0x9d, 0x00, 0x90, 	/*Color of index 4*/
  0xb8, 0x9c, 0x00, 0xef, 	/*Color of index 5*/
  0xb9, 0x9d, 0x00, 0xff, 	/*Color of index 6*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 7*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 8*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 9*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 10*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 11*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 12*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 13*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 14*/
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 15*/

  0x02, 0x55, 0x30, 
  0x46, 0x66, 0x61, 
  0x56, 0x66, 0x65, 
  0x56, 0x66, 0x65, 
  0x16, 0x66, 0x63, 
  0x03, 0x55, 0x10, 
};

const lv_img_dsc_t ICON_PAGE_DOT_SELECTED = {
  .header.cf = LV_IMG_CF_INDEXED_4BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 6,
  .header.h = 6,
  .data_size = 83,
  .data = ICON_PAGE_DOT_SELECTED_map,
};
