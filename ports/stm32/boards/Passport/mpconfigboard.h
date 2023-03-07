// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#define MICROPY_HW_BOARD_NAME "Passport"
#define MICROPY_HW_MCU_NAME "STM32H753"

#define MICROPY_PASSPORT

/* MicroPython settings */
#define MICROPY_PY_NETWORK (0)
#define MICROPY_PY_USOCKET (0)
#define MICROPY_PY_UHASHLIB_SHA256 (0)
#define MICROPY_PY_STM (0)
#define MICROPY_PY_PYB_LEGACY (0)
#define MICROPY_PY_ONEWIRE (0)
#define MICROPY_PY_THREAD (1)

#ifndef MICROPY_PY_MACHINE
#define MICROPY_PY_MACHINE          (1)
#define MICROPY_PY_MACHINE_PULSE    (1)
#define MICROPY_PY_MACHINE_PIN_MAKE_NEW mp_pin_make_new
#define MICROPY_PY_MACHINE_I2C      (0)
#define MICROPY_PY_MACHINE_SPI      (1)
#define MICROPY_PY_MACHINE_SPI_MSB  (SPI_FIRSTBIT_MSB)
#define MICROPY_PY_MACHINE_SPI_LSB  (SPI_FIRSTBIT_LSB)
#endif

/* MicroPython hardware peripheral settings */
#define MICROPY_HW_ENABLE_RTC (0)
#define MICROPY_HW_ENABLE_RNG (1)
#define MICROPY_HW_ENABLE_ADC (1)
#define MICROPY_HW_ENABLE_DAC (0)
#define MICROPY_HW_ENABLE_USB (0)
#define MICROPY_HW_ENABLE_SDCARD (1)
#define MICROPY_HW_ENABLE_DCMI (1)
#define MICROPY_HW_HAS_SWITCH (0)

/* Turn off the internal flash file system */
#define MICROPY_HW_HAS_FLASH (0)
#define MICROPY_HW_ENABLE_INTERNAL_FLASH_STORAGE (0)
#define MICROPY_HW_USB_MSC (0)

#define PASSPORT_FOUNDATION_ENABLED (1)

#define MICROPY_BOARD_EARLY_INIT Passport_board_early_init
void Passport_board_early_init(void);

#define MICROPY_BOARD_INIT Passport_board_init
void Passport_board_init(void);

/**
 * The following two macros disable interrupts preserving interrupt state
 * and then properly handle getting the keypad controller to pulse the
 * interrupt pin if there are keypad events in its FIFO.
 *
 * Usage
 * #include "py/obj.h"
 * #include "keypad-adp-5587.h"
 *
 * In the function where you need to disable interrupts
 * mp_uint_t interrupt_state;
 * interrupt_state = PASSPORT_KEYPAD_BEGIN_ATOMIC_SECTION();
 * function_call();
 * PASSPORT_KEYPAD_END_ATOMIC_SECTION(interrupt_state);
 */
#define PASSPORT_KEYPAD_BEGIN_ATOMIC_SECTION() disable_irq()
#define PASSPORT_KEYPAD_END_ATOMIC_SECTION(state) \
    enable_irq(state);                            \
    keypad_write(get_kbd_addr(), KBD_REG_INT_STAT, 0xFF)

// The board has an 8MHz HSE, the following gives 480MHz CPU speed
#define MICROPY_HW_CLK_PLLM (1)
#define MICROPY_HW_CLK_PLLN (120)  //(19)
#define MICROPY_HW_CLK_PLLP (2)
#define MICROPY_HW_CLK_PLLQ (120)  //(38)
#define MICROPY_HW_CLK_PLLR (2)

#define MICROPY_HW_CLK_PLL3M (1)
#define MICROPY_HW_CLK_PLL3N (18)
#define MICROPY_HW_CLK_PLL3P (1)
#define MICROPY_HW_CLK_PLL3Q (2)
#define MICROPY_HW_CLK_PLL3R (2)

// 4 wait states
#define MICROPY_HW_FLASH_LATENCY FLASH_LATENCY_4

// UART config
#define MICROPY_HW_UART2_TX (pin_A2)
#define MICROPY_HW_UART2_RX (pin_A3)
#define MICROPY_HW_UART2_RTS (pin_A1)
#define MICROPY_HW_UART2_CTS (pin_A0)

#define MICROPY_HW_HAS_GPIOE (1)

#define MICROPY_HW_UART_REPL PYB_UART_2
#define MICROPY_HW_UART_REPL_BAUD 115200

// SPI
#define MICROPY_HW_SPI1_NSS (pin_A15)
#define MICROPY_HW_SPI1_SCK (pin_A5)
#define MICROPY_HW_SPI1_MOSI (pin_A7)

#define MICROPY_HW_SPI4_NSS (pin_E11)
#define MICROPY_HW_SPI4_SCK (pin_E12)
#define MICROPY_HW_SPI4_MISO (pin_E13)
#define MICROPY_HW_SPI4_MOSI (pin_E14)

// SD card detect switch
#define MICROPY_HW_SDCARD_DETECT_PIN (pin_E3)
#define MICROPY_HW_SDCARD_DETECT_PULL (GPIO_PULLUP)
#define MICROPY_HW_SDCARD_DETECT_PRESENT (GPIO_PIN_RESET)

// BQ27520 fuel gauge
#define MICROPY_HW_BQ27520_BAT_LOW_PIN (pin_E9)
#define MICROPY_HW_BQ27520_SOC_INT_PIN (pin_E10)

// LCD Teariing Effect output line
#define MICROPY_HW_LCD_TE_PIN (pin_B5)
#define MICROPY_HW_LCD_TE_PULL (GPIO_NOPULL)
