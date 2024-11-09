// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(target_arch = "arm", no_std)]
#![allow(non_camel_case_types)]

#[cfg(target_arch = "arm")]
use cortex_m as _;

pub mod firmware;
pub mod flash;
pub mod secp256k1;
pub mod ur;

/// cbindgen:ignore
#[cfg(all(target_os = "none", target_arch = "arm"))]
mod rand;
/// cbindgen:ignore
#[cfg(target_os = "none")]
mod stdout;

#[cfg(target_os = "none")]
#[panic_handler]
fn panic_handler(info: &core::panic::PanicInfo) -> ! {
    use core::fmt::Write;

    let mut stdout = stdout::Stdout;
    writeln!(stdout, "{}", info).ok();

    loop {}
}
