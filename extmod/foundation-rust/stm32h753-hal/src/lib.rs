// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! # Hardware Abstraction Layer (HAL) for STM32H753.
//!
//! This is an alternative to the `stm32h7xx-hal` but without the complexity as
//! that crate tries to reconfigure all of the peripherals, including RCC, and
//! that is handled already by the MicroPython code. So, it doesn't integrate
//! well with this codebase.

#![no_std]

pub mod gpio;
pub mod rcc;
