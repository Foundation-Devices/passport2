// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: BSD-3-Clause
//

/*-----------------------------------------------------------------------------
 * Copyright (c) 2013 - 2019 Arm Limited (or its affiliates). All
 * rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *   1.Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *   2.Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *   3.Neither the name of Arm nor the names of its contributors may be used
 *     to endorse or promote products derived from this software without
 *     specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDERS AND CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *-----------------------------------------------------------------------------
 * Name:    Board_Camera.h
 * Purpose: Digital camera interface header file
 * Rev.:    1.0.0
 *----------------------------------------------------------------------------*/

#ifndef __CAMERA_OVM7690_H
#define __CAMERA_OVM7690_H

#include <stdint.h>
#include "framebuffer.h"

#define CAMERA_I2C_ADDR (0x21 << 1)  // Use 8-bit address

/* Camera registers */
#define GAIN 0x00
#define BGAIN 0x01
#define RGAIN 0x02
#define GGAIN 0x03
#define YAVG 0x04
#define BAVG 0x05
#define RAVG 0x06
/* 0x08 - 0x09 reserved */
#define PIDH 0x0A
#define PIDL 0x0B
#define REG0C 0x0C
#define REG0D 0x0D
#define REG0E 0x0E
#define AECH 0x0F
#define AECL 0x10
#define CLKRC 0x11
#define REG12 0x12
#define REG13 0x13
#define REG14 0x14
#define REG15 0x15
#define REG16 0x16
#define HSTART 0x17
#define HSIZE 0x18
#define VSTART 0x19
#define VSIZE 0x1A
#define SHFT 0x1B
#define MIDH 0x1C
#define MIDL 0x1D
/* 0x1E - 0x1F reserved */
#define REG20 0x20
#define AECGM 0x21
#define REG22 0x22
/* 0x23 reserved */
#define WPT 0x24
#define BPT 0x25
#define VPT 0x26
#define REG27 0x27
#define REG28 0x28
#define PLL 0x29
#define EXHCL 0x2A
#define EXHCH 0x2B
#define DM_LN 0x2C
#define ADVFL 0x2D
#define ADVFH 0x2E
/* 0x2F - 0x37 reserved */
#define SOC 0x38
/* 0x39 - 0x3D reserved */
#define REG3E 0x3E
#define REG3F 0x3F
/* 0x40 - 0x47 reserved */
#define ANA1 0x48
#define PWC0 0x49
/* 0x4A - 0x4F reserved */
#define BD50ST 0x50
#define BD60ST 0x51
/* 0x52 - 0x59 reserved */
#define UVCTR0 0x5A
#define UVCTR1 0x5B
#define UVCTR2 0x5C
#define UVCTR3 0x5D
/* 0x5E - 0x61 reserved */
#define REG62 0x62
/* 0x63 - 0x67 reserved */
#define BLC8 0x68
/* 0x69 - 0x6A reserved */
#define BLCOUT 0x6B
/* 0x6C - 0x6E reserved */
#define REG6F 0x6F
/* 0x70 - 0x7F reserved */
#define REG80 0x80
#define REG81 0x81
#define REG82 0x82
/* 0x83 - 0x84 reserved */
#define LCC0 0x85
#define LCC1 0x86
#define LCC2 0x87
#define LCC3 0x88
#define LCC4 0x89
#define LCC5 0x8A
#define LCC6 0x8B
/* 0x8C - 0xA2 AWB Control Registers */
#define GAM1 0xA3
#define GAM2 0xA4
#define GAM3 0xA5
#define GAM4 0xA6
#define GAM5 0xA7
#define GAM6 0xA8
#define GAM7 0xA9
#define GAM8 0xAA
#define GAM9 0xAB
#define GAM10 0xAC
#define GAM11 0xAD
#define GAM12 0xAE
#define GAM13 0xAF
#define GAM14 0xB0
#define GAM15 0xB1
#define SLOPE 0xB2
/* 0xB3 reserved */
#define REGB4 0xB4
#define REGB5 0xB5
#define REGB6 0xB6
#define REGB7 0xB7
#define REGB8 0xB8
#define REGB9 0xB9
#define REGBA 0xBA
#define REGBB 0xBB
#define REGBC 0xBC
#define REGBD 0xBD
#define REGBE 0xBE
#define REGBF 0xBF
#define REGC0 0xC0
#define REGC1 0xC1
#define REGC2 0xC2
#define REGC3 0xC3
#define REGC4 0xC4
#define REGC5 0xC5
#define REGC6 0xC6
#define REGC7 0xC7
#define REGC8 0xC8
#define REGC9 0xC9
#define REGCA 0xCA
#define REGCB 0xCB
#define REGCC 0xCC
#define REGCD 0xCD
#define REGCE 0xCE
#define REGCF 0xCF
#define REGD0 0xD0
/* 0xD1 reserved */
#define REGD2 0xD2
#define REGD3 0xD3
#define REGD4 0xD4
#define REGD5 0xD5
#define REGD6 0xD6
#define REGD7 0xD7
#define REGD8 0xD8
#define REGD9 0xD9
#define REGDA 0xDA
#define REGDB 0xDB
#define REGDC 0xDC
#define REGDD 0xDD
#define REGDE 0xDE
#define REGDF 0xDF
#define REGE0 0xE0
#define REGE1 0xE1

// Initialize the camera.
HAL_StatusTypeDef camera_init(void);

// Turn on the camera.
HAL_StatusTypeDef camera_on(void);

// Turn off the camera.
HAL_StatusTypeDef camera_off(void);

// Take a snapshot using the camera.
HAL_StatusTypeDef camera_snapshot(void);

#endif /* __CAMERA_OVM7960_H */
