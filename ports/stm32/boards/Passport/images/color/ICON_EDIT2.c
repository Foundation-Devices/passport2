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
#ifndef LV_ATTRIBUTE_IMG_ICON_EDIT2
#define LV_ATTRIBUTE_IMG_ICON_EDIT2
#endif
const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_IMG_ICON_EDIT2 uint8_t ICON_EDIT2_map[] = {
  0x00, 0x00, 0x00, 0x00, 	/*Color of index 0*/
  0xff, 0xff, 0xff, 0x20, 	/*Color of index 1*/
  0xfe, 0xfe, 0xfe, 0x65, 	/*Color of index 2*/
  0xfe, 0xfe, 0xfe, 0xee, 	/*Color of index 3*/

  0x00, 0x00, 0x00, 0x00, 0x50, 
  0x00, 0x00, 0x00, 0x07, 0xf8, 
  0x06, 0xaa, 0x90, 0x1f, 0xbd, 
  0x2f, 0xff, 0xf0, 0x7d, 0x2d, 
  0x79, 0x55, 0x51, 0xf4, 0x7c, 
  0x78, 0x00, 0x07, 0xd1, 0xf4, 
  0x78, 0x00, 0x1f, 0x47, 0xd0, 
  0x78, 0x00, 0x7d, 0x1f, 0x40, 
  0x78, 0x01, 0xf4, 0x7d, 0x00, 
  0x78, 0x07, 0xd1, 0xf4, 0x00, 
  0x78, 0x0b, 0x47, 0xd1, 0xd0, 
  0x78, 0x0f, 0x1f, 0x41, 0xe0, 
  0x78, 0x0f, 0xfd, 0x01, 0xe0, 
  0x78, 0x1f, 0xa4, 0x01, 0xe0, 
  0x78, 0x04, 0x00, 0x01, 0xe0, 
  0x78, 0x00, 0x00, 0x01, 0xe0, 
  0x78, 0x00, 0x00, 0x01, 0xe0, 
  0x3e, 0xaa, 0xaa, 0xaa, 0xe0, 
  0x1f, 0xff, 0xff, 0xff, 0x80, 
  0x01, 0x55, 0x55, 0x55, 0x00, 
};

const lv_img_dsc_t ICON_EDIT2 = {
  .header.cf = LV_IMG_CF_INDEXED_2BIT,
  .header.always_zero = 0,
  .header.reserved = 0,
  .header.w = 20,
  .header.h = 20,
  .data_size = 117,
  .data = ICON_EDIT2_map,
};