// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use stm32h7::stm32h753::rcc::RegisterBlock;

pub trait Enable {
    fn enable(&self, rcc: &RegisterBlock);
}
