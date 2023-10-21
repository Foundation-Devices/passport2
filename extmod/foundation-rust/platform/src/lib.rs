// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(all(target_arch = "arm", target_os = "none"), no_std)]

/// Enables STM32-specific code.
#[macro_export]
macro_rules! cfg_stm32 {
    ($($item:item)*) => {
        $(
            #[cfg(all(target_arch = "arm", target_os = "none"))]
            $item
        )*
    }
}

/// Enables unix-specific code.
#[macro_export]
macro_rules! cfg_unix {
    ($($item:item)*) => {
        $(
            #[cfg(target_family = "unix")]
            $item
        )*
    }
}

cfg_stm32! {
    mod stm32;
    pub use self::stm32::*;

    /// Panic handler.
    ///
    /// This only serves as a debugging tool for Rust code on the development
    /// boards because it only prints to the serial port the panic information.
    ///
    /// TODO: Pass this back as an exception to MicroPython, to avoid hangs.
    #[panic_handler]
    fn panic_handler(info: &core::panic::PanicInfo) -> ! {
        use core::fmt::Write;

        let mut stdout = crate::io::stdout();
        writeln!(stdout, "{}", info).ok();

        loop {}
    }
}

cfg_unix! {
    mod unix;
    pub use self::unix::*;
}
