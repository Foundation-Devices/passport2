// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(target_arch = "arm", no_std)]
#![allow(non_camel_case_types)]

#[cfg(target_arch = "arm")]
use cortex_m as _;

pub mod bip32;
pub mod firmware;
pub mod flash;
pub mod psbt;
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

pub struct Logger;

impl log::Log for Logger {
    fn enabled(&self, _: &log::Metadata) -> bool {
        true
    }

    fn log(&self, record: &log::Record) {
        #[cfg(target_arch = "arm")]
        {
            use core::fmt::Write;

            writeln!(stdout::Stdout, "[{}]: {}", record.level(), record.args())
                .ok();
        }

        #[cfg(not(target_arch = "arm"))]
        println!("[{}]: {}", record.level(), record.args());
    }

    fn flush(&self) {}
}

/// cbindgen:ignore
static LOGGER: Logger = Logger;

/// Initialize the Rust logger.
#[export_name = "foundation_init_logger"]
pub unsafe extern "C" fn init_logger() {
    log::set_logger_racy(&LOGGER)
        .map(|()| log::set_max_level(log::LevelFilter::Debug))
        .expect("Failed to initialize logger")
}
