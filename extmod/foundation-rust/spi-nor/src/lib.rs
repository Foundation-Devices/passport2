// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#![no_std]

use bitflags::bitflags;
use embedded_hal::blocking::spi::Transfer;
use embedded_hal::digital::v2::OutputPin;

/// A SPI NOR memory flash.
#[derive(Debug)]
pub struct Flash<SPI: Transfer<u8>, CS: OutputPin> {
    spi: SPI,
    cs: CS,
}

impl<SPI: Transfer<u8>, CS: OutputPin> Flash<SPI, CS> {
    pub fn new(spi: SPI, cs: CS) -> Self {
        Self { spi, cs }
    }

    /// Probe that the flash memory is present.
    pub fn probe(&mut self) -> Result<(), Error<SPI, CS>> {
        self.read_jedec_id()?;
        Ok(())
    }

    /// Reads the status register.
    pub fn read_status(&mut self) -> Result<Status, Error<SPI, CS>> {
        let mut buf = [Instruction::ReadStatusRegister as u8, 0];
        let res = self.transfer(&mut buf)?;
        Ok(Status::from_bits(res[0])
            .expect("all of status bits should be defined"))
    }

    /// Reads the JEDEC ID.
    pub fn read_jedec_id(&mut self) -> Result<(), Error<SPI, CS>> {
        let mut buf = [Instruction::ReadJedecId as u8, 0, 0, 0];
        let _res = self.transfer(&mut buf)?;
        Ok(())
    }

    fn transfer<'b>(
        &mut self,
        buf: &'b mut [u8],
    ) -> Result<&'b [u8], Error<SPI, CS>> {
        self.cs.set_low().map_err(Error::Pin)?;
        let result = self.spi.transfer(buf).map_err(Error::Spi);
        self.cs.set_high().map_err(Error::Pin)?;
        result
    }
}

pub enum Error<SPI: Transfer<u8>, CS: OutputPin> {
    Spi(SPI::Error),
    Pin(CS::Error),
}

#[derive(Debug)]
enum Instruction {
    ReadStatusRegister = 0x05,
    ReadJedecId = 0x9F,
}

bitflags! {
    pub struct Status: u8 {
        const BUSY = 1 << 0;
        const WEL  = 1 << 1;
        const BP0  = 1 << 2;
        const BP1  = 1 << 3;
        const BP2  = 1 << 4;
        const TB   = 1 << 5;
        const SEC  = 1 << 6;
        const SRP  = 1 << 7;
    }
}
