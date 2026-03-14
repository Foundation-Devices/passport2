// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use core::{ffi::c_int, fmt};

pub struct Stdout;

impl fmt::Write for Stdout {
    fn write_str(&mut self, s: &str) -> core::fmt::Result {
        for &c in s.as_bytes() {
            unsafe {
                putchar(c as c_int);
            }
        }

        Ok(())
    }
}

extern "C" {
    fn putchar(c: c_int) -> c_int;
}
