// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later


pub type Flash = spi_nor::Flash<EmulatedSpiBus, EmulatedPin>;

pub struct EmulatedSpiBus;

pub struct EmulatedPin;
