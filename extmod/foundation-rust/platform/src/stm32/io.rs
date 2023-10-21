// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

pub mod spi;

use crate::stm32::ffi;

/// Returns a handle to the standard output.
pub fn stdout() -> Stdout {
    Stdout { __private: () }
}

/// Standard output handle, created by [`stdout`].
#[derive(Debug)]
pub struct Stdout {
    __private: (),
}

impl core::fmt::Write for Stdout {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        for &c in s.as_bytes() {
            unsafe {
                ffi::putchar(c as core::ffi::c_int);
            }
        }

        Ok(())
    }
}
