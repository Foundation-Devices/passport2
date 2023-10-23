// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#[repr(C)]
pub struct SPI_Flash_t {
    flash: passport_platform::io::Flash,
}

/// Read from the SPI NOR flash memory.
pub fn spi_nor_read(dev: &mut spi_nor_t, address: u32, buf: *mut u8, len: usize) {
    let buf = unsafe { core::slice::from_raw_parts(buf, len) };
    todo!()
    //dev.flash.read(address, buf).unwrap()
}
