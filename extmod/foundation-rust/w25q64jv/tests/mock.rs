// Mock tests for Winbond W25Q64JV SPI flash.
//
// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use embedded_hal_mock::eh1::spi;
use w25q64jv::{command, Status1, W25Q64JV};

#[test]
fn test_read_status_1() {
    let status1 = Status1::all();
    let expectations = [
        spi::Transaction::transaction_start(),
        spi::Transaction::write(command::READ_STATUS_REGISTER_1),
        spi::Transaction::read(status1.bits()),
        spi::Transaction::transaction_end(),
    ];

    let mut spi = spi::Mock::new(&expectations);
    let mut flash = W25Q64JV::new(&mut spi);
    assert_eq!(flash.read_status_1().unwrap(), status1);

    spi.done();
}
