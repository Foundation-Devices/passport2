// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! # MicroPython STM32 bindings and runtime for Rust.
//!
//! Runtime code and bindings for MicroPython STM32 port.  This crate assumes
//! that it will be linked into MicroPython.

#![no_std]

// This forces Rust to include this crate as it provides symbols for
// critical-section.
use cortex_m as _;

mod ffi;
mod rt;

pub mod io;
pub mod rand;
pub mod secp256k1;
