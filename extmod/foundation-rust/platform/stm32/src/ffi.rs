// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! FFI bindings to the MicroPython STM32 port.
//!
//! These bindings do not use rust-bindings to decrease the complexity of the
//! build-system, mainly because the preprocessing steps of MicroPython are
//! too complicated as it first requires preprocessing all of the code for
//! extracting QSTRs, etc.
//!
//! The aim of this module is to keep it simple and detect which types are
//! really needed so keep an interface with MicroPython as minimal as
//! possible.
//!
//! Code that depends on preprocessor assumptions should be documented
//! properly.
//!
//! FIXME: If there's enough interest for replacing more MicroPython code
//! in the future one could start by removing the bindings for SPI, Pin,
//! etc. and handle those in pure Rust with embedded-hal and stm32h7xx-hal
//! maybe.
//!
//! That would require porting code that interacts with most devices to Rust
//! first.

use core::ffi::{c_int, c_void};

pub const NOISE_AVALANCHE_SOURCE: u8 = 1 << 0;
pub const NOISE_MCU_RNG_SOURCE: u8 = 1 << 1;
pub const NOISE_SE_RNG_SOURCE: u8 = 1 << 2;
pub const NOISE_ALL: u8 =
    NOISE_AVALANCHE_SOURCE | NOISE_MCU_RNG_SOURCE | NOISE_SE_RNG_SOURCE;

#[repr(C)]
pub struct spi_t {
    spi: *mut c_void,            // SPI_HandleTypeDef *.
    tx_dma_descr: *const c_void, // dma_descr_t *.
    rx_dma_descr: *const c_void, // dma_descr_t *.
}

extern "C" {
    // C standard library.
    pub fn putchar(c: c_int) -> c_int;

    // Crypto RNG.
    pub fn noise_enable();
    pub fn noise_disable();
    pub fn noise_get_random_bytes(
        sources: u8,
        buf: *mut c_void,
        buf_len: usize,
    ) -> bool;

    // SPI.
    pub static spi_obj: [spi_t; 6];
    pub fn spi_transfer(
        self_: *const spi_t,
        len: usize,
        src: *const u8,
        dest: *mut u8,
        timeout: u32,
    );
}
