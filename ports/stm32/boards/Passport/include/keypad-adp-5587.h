// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef KEYPAD_H_
#define KEYPAD_H_

#include <stdint.h>
#include "ring_buffer.h"
#include "stm32h7xx_hal_dma.h"
#include "stm32h7xx_hal_i2c.h"
#include "i2c-init.h"

// Use 8-Bit address
#define KBD_ADDR_REV_A (0x34 << 1)
#define KBD_ADDR_REV_B (0x30 << 1)

#define KBD_REG_DEVID 0x00            // Device ID
#define KBD_REG_CFG 0x01              // Configuration Register 1
#define KBD_REG_INT_STAT 0x02         // Interrupt status register
#define KBD_REG_KEY_LCK_EC_STAT 0x03  // Keylock and event counter register

#define KBD_REG_KEY_EVENTA 0x04  // Key Event Register A
#define KBD_REG_KEY_EVENTB 0x05  // Key Event Register B
#define KBD_REG_KEY_EVENTC 0x06  // Key Event Register C
#define KBD_REG_KEY_EVENTD 0x07  // Key Event Register D
#define KBD_REG_KEY_EVENTE 0x08  // Key Event Register E
#define KBD_REG_KEY_EVENTF 0x09  // Key Event Register F
#define KBD_REG_KEY_EVENTG 0x0A  // Key Event Register G
#define KBD_REG_KEY_EVENTH 0x0B  // Key Event Register H
#define KBD_REG_KEY_EVENTI 0x0C  // Key Event Register I
#define KBD_REG_KEY_EVENTJ 0x0D  // Key Event Register J

#define KBD_REG_KP_LCK_TMR 0x0E  // Keypad Unlock 1 timer to Keypad Unlock 2 timer
#define KBD_REG_UNLOCK1 0x0F     // Unlock Key 1
#define KBD_REG_UNLOCK2 0x10     // Unlock Key 2

#define KBD_REG_GPIO_INT_STAT1 0x11  // GPIO interrupt status
#define KBD_REG_GPIO_INT_STAT2 0x12  // GPIO interrupt status
#define KBD_REG_GPIO_INT_STAT3 0x13  // GPIO interrupt status

#define KBD_REG_GPIO_DAT_STAT1 0x14  // GPIO data status
#define KBD_REG_GPIO_DAT_STAT2 0x15  // GPIO data status
#define KBD_REG_GPIO_DAT_STAT3 0x16  // GPIO data status

#define KBD_REG_GPIO_DAT_OUT1 0x17  // GPIO data out
#define KBD_REG_GPIO_DAT_OUT2 0x18  // GPIO data out
#define KBD_REG_GPIO_DAT_OUT3 0x19  // GPIO data out

#define KBD_REG_GPIO_INT_EN1 0x1A  // GPIO interrupt enable
#define KBD_REG_GPIO_INT_EN2 0x1B  // GPIO interrupt enable
#define KBD_REG_GPIO_INT_EN3 0x1C  // GPIO interrupt enable

#define KBD_REG_KP_GPIO1 0x1D  // Keypad or GPIO selection
#define KBD_REG_KP_GPIO2 0x1E  // Keypad or GPIO selection
#define KBD_REG_KP_GPIO3 0x1F  // Keypad or GPIO selection

#define KBD_REG_GPI_EM_REG1 0x20  // GPI Event Mode 1
#define KBD_REG_GPI_EM_REG2 0x21  // GPI Event Mode 2
#define KBD_REG_GPI_EM_REG3 0x22  // GPI Event Mode 3

#define KBD_REG_GPIO_DIR1 0x23  // GPIO data direction
#define KBD_REG_GPIO_DIR2 0x24  // GPIO data direction
#define KBD_REG_GPIO_DIR3 0x25  // GPIO data direction

#define KBD_REG_GPIO_INT_LVL1 0x26  // GPIO level detect
#define KBD_REG_GPIO_INT_LVL2 0x27  // GPIO level detect
#define KBD_REG_GPIO_INT_LVL3 0x28  // GPIO level detect

#define KBD_REG_DEBOUNCE_DIS1 0x29  // Debounce disable
#define KBD_REG_DEBOUNCE_DIS2 0x2A  // Debounce disable
#define KBD_REG_DEBOUNCE_DIS3 0x2B  // Debounce disable

#define KBD_REG_GPIO_PULL1 0x2C  // GPIO pull disable
#define KBD_REG_GPIO_PULL2 0x2D  // GPIO pull disable
#define KBD_REG_GPIO_PULL3 0x2E  // GPIO pull disable

#define KBD_REG_CFG_AUTO_INC 0x80
#define KBD_REG_CFG_GPIEM_CFG 0x40
#define KBD_REG_CFG_OVR_FLOW_M 0x20
#define KBD_REG_CFG_INT_CFG 0x10
#define KBD_REG_CFG_OVR_FLOW_IEN 0x08
#define KBD_REG_CFG_K_LCK_IM 0x04
#define KBD_REG_CFG_GPI_IEN 0x02
#define KBD_REG_CFG_KE_IEN 0x01

extern bool keypad_init(void);
extern int  keypad_write(uint8_t address, uint8_t reg, uint8_t data);
extern int  keypad_read(uint8_t address, uint8_t reg, uint8_t* data, uint8_t len);
extern void keypad_test(void);
extern void keypad_ISR(void);
extern bool keypad_poll_key(uint8_t* key);

uint8_t get_kbd_addr(void);
bool read_num_keys(uint8_t *num_keys);

#endif
