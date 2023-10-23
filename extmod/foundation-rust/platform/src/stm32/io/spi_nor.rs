// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use crate::io::spi::Spi;
use stm32h753_hal::gpio::{Output, gpioe::PE11};

pub type Flash = Flash<Spi, PE11<Output>>;
