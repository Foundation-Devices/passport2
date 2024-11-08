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
pub const GPIOE: *mut GPIO_TypeDef = GPIOE_BASE as *mut GPIO_TypeDef;
pub const RCC: *mut RCC_TypeDef = RCC_BASE as *mut RCC_TypeDef;
pub const SPI1: *mut SPI_TypeDef = SPI1_BASE as *mut SPI_TypeDef;
pub const SPI2: *mut SPI_TypeDef = SPI2_BASE as *mut SPI_TypeDef;
pub const SPI3: *mut SPI_TypeDef = SPI3_BASE as *mut SPI_TypeDef;
pub const SPI4: *mut SPI_TypeDef = SPI4_BASE as *mut SPI_TypeDef;
pub const SPI5: *mut SPI_TypeDef = SPI5_BASE as *mut SPI_TypeDef;
pub const SPI6: *mut SPI_TypeDef = SPI6_BASE as *mut SPI_TypeDef;
