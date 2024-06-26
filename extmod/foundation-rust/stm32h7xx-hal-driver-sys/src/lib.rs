// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
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
pub const SPI1: *mut SPI_TypeDef = SPI1_BASE as *mut SPI_TypeDef;
pub const SPI2: *mut SPI_TypeDef = SPI2_BASE as *mut SPI_TypeDef;
pub const SPI3: *mut SPI_TypeDef = SPI3_BASE as *mut SPI_TypeDef;
pub const SPI4: *mut SPI_TypeDef = SPI3_BASE as *mut SPI_TypeDef;
pub const SPI5: *mut SPI_TypeDef = SPI3_BASE as *mut SPI_TypeDef;
pub const SPI6: *mut SPI_TypeDef = SPI3_BASE as *mut SPI_TypeDef;

pub const HAL_SPI_ERROR_NONE: u32 = 0x00000000;
pub const HAL_SPI_ERROR_MODF: u32 = 0x00000001;
pub const HAL_SPI_ERROR_CRC: u32 = 0x00000002;
pub const HAL_SPI_ERROR_OVR: u32 = 0x00000004;
pub const HAL_SPI_ERROR_FRE: u32 = 0x00000008;
pub const HAL_SPI_ERROR_DMA: u32 = 0x00000010;
pub const HAL_SPI_ERROR_FLAG: u32 = 0x00000020;
pub const HAL_SPI_ERROR_ABORT: u32 = 0x00000040;
pub const HAL_SPI_ERROR_UDR: u32 = 0x00000080;
pub const HAL_SPI_ERROR_TIMEOUT: u32 = 0x00000100;
pub const HAL_SPI_ERROR_UNKNOW: u32 = 0x00000200; // Typo is on the HAL too.
pub const HAL_SPI_ERROR_NOT_SUPPORTED: u32 = 0x00000400;
pub const HAL_SPI_ERROR_INVALID_CALLBACK: u32 = 0x00000800;
