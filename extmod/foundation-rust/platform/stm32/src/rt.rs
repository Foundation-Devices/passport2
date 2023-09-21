// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

/// Panic handler.
///
/// This only serves as a debugging tool for Rust code on the development
/// boards because it only prints to the serial port the panic information.
///
/// TODO: Pass this back as an exception to MicroPython, to avoid hangs.
#[panic_handler]
#[cfg(all(target_arch = "arm", target_os = "none"))]
fn panic_handler(info: &core::panic::PanicInfo) -> ! {
    use core::fmt::Write;

    let mut stdout = crate::io::stdout();
    writeln!(stdout, "{}", info).ok();

    loop {}
}
