// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#![no_std]

// Bindgen generated.
#[allow(non_camel_case_types)]
#[allow(non_snake_case)]
#[allow(non_upper_case_globals)]
#[rustfmt::skip]
mod gen;
pub use self::gen::*;

// Manually generated code.
//
// Bindgen doesn't support generating constants from `#define`s with pointer
// casts. See <https://github.com/rust-lang/rust-bindgen/issues/2732>.
pub const GPIO_AF5_SPI4: u8 = 0x05;
pub const GPIO_PIN_0: u16 = 0x0001;
pub const GPIO_PIN_1: u16 = 0x0002;
pub const GPIO_PIN_2: u16 = 0x0004;
pub const GPIO_PIN_3: u16 = 0x0008;
pub const GPIO_PIN_4: u16 = 0x0010;
pub const GPIO_PIN_5: u16 = 0x0020;
pub const GPIO_PIN_6: u16 = 0x0040;
pub const GPIO_PIN_7: u16 = 0x0080;
pub const GPIO_PIN_8: u16 = 0x0100;
pub const GPIO_PIN_9: u16 = 0x0200;
pub const GPIO_PIN_10: u16 = 0x0400;
pub const GPIO_PIN_11: u16 = 0x0800;
pub const GPIO_PIN_12: u16 = 0x1000;
pub const GPIO_PIN_13: u16 = 0x2000;
pub const GPIO_PIN_14: u16 = 0x4000;
pub const GPIO_PIN_15: u16 = 0x8000;
pub const SPI_DIRECTION_2LINES: u32 = 0x00000000;
