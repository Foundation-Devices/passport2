// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Driver for SPI-NOR memory flashes.
//!
//! NOTE: perhaps this requires it's own repository if we need it for anything
//! else.
//!
//! TODO: This could be tested with qemu.
//!
//! See:
//!
//! https://github.com/qemu/qemu/blob/master/hw/block/m25p80.c

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

    /// Read from the memory.
    ///
    /// # Errors
    ///
    /// Returns [`nb::Error::WouldBlock`] if the memory has not finished yet
    /// an operation.
    pub fn read(
        &mut self,
        address: u32,
        buf: &mut [u8],
    ) -> nb::Result<(), Error<SPI, CS>> {
        let status = self.read_status()?;
        if status.intersects(Status::BUSY) {
            return Err(nb::Error::WouldBlock);
        }

        let mut instruction = [
            Instruction::ReadData as u8,
            ((address >> 16) & 0xFF) as u8,
            ((address >> 8) & 0xFF) as u8,
            (address & 0xFF) as u8,
        ];

        self.cs.set_low().map_err(Error::Pin)?;

        // Send the READ DATA instruction first.
        let result = self.spi.transfer(&mut instruction).map_err(Error::Spi);
        if result.is_err() {
            self.cs.set_high().map_err(Error::Pin)?;
            return Err(nb::Error::Other(result.unwrap_err()));
        }

        // Perform the read.
        let result = self.spi.transfer(buf).map_err(Error::Spi);

        self.cs.set_high().map_err(Error::Pin)?;

        result?;

        Ok(())
    }

    /// Reads the status register.
    pub fn read_status(&mut self) -> Result<Status, Error<SPI, CS>> {
        let mut buf = [Instruction::ReadStatusRegister as u8, 0];
        let res = self.instruction(&mut buf)?;
        Ok(Status::from_bits(res[0])
            .expect("all of status bits should be defined"))
    }

    fn instruction<'b>(
        &mut self,
        buf: &'b mut [u8],
    ) -> Result<&'b [u8], Error<SPI, CS>> {
        self.cs.set_low().map_err(Error::Pin)?;
        let result = self.spi.transfer(buf).map_err(Error::Spi);
        self.cs.set_high().map_err(Error::Pin)?;
        result
    }
}

#[derive(Debug)]
pub enum Error<SPI: Transfer<u8>, CS: OutputPin> {
    /// SPI error.
    Spi(SPI::Error),
    /// GPIO pin error.
    Pin(CS::Error),
}

#[derive(Debug)]
enum Instruction {
    ReadData = 0x03,
    ReadStatusRegister = 0x05,
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
