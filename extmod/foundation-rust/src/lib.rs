// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(not(feature = "std"), no_std)]
#![allow(non_camel_case_types)]

pub mod ur;

/// cbindgen:ignore
#[cfg(not(feature = "std"))]
mod stdout;

#[panic_handler]
#[cfg(all(not(feature = "std"), not(test)))]
fn panic_handler(info: &core::panic::PanicInfo) -> ! {
    use core::fmt::Write;

    let mut stdout = stdout::Stdout;
    writeln!(stdout, "{}", info).ok();

    loop {}
}
