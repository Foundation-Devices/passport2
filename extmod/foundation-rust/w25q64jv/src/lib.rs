// Driver for Winbond W25Q64JV SPI flash.
//
// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Winbond W25Q64JV SPI flash driver.
//!
//! This crate provides a minimal driver over a
//! [`embedded_hal::spi::SpiDevice`] for the W25Q64JV SPI NOR flash.

#![no_std]

use bitflags::bitflags;
use core::fmt::Debug;
use embedded_hal::spi::{Operation, SpiDevice};
use embedded_storage::nor_flash::{
    ErrorType, NorFlash, NorFlashError, NorFlashErrorKind, ReadNorFlash,
};

pub mod command {
    pub const PAGE_PROGRAM: u8 = 0x02;
    pub const READ_STATUS_REGISTER_1: u8 = 0x05;
    pub const FAST_READ: u8 = 0x0B;
    pub const WRITE_ENABLE: u8 = 0x06;
    pub const SECTOR_ERASE: u8 = 0x20;
    pub const BLOCK_ERASE_64KIB: u8 = 0xD8;
}

bitflags! {
    // Status 1 register bits.
    #[derive(Debug, PartialEq, Eq)]
    pub struct Status1: u8 {
        /// Write in progress.
        const BUSY = 1 << 0;
        /// Write enable latch.
        const WEL = 1 << 1;
        const BP0 = 1 << 2;
        const BP1 = 1 << 3;
        const BP2 = 1 << 4;
        const TB = 1 << 5;
        const SEC = 1 << 6;
        const SRP = 1 << 7;
    }
}

/// Driver for Winbond W25Q64JV SPI flash.
#[derive(Debug)]
pub struct W25Q64JV<D> {
    device: D,
}

impl<D> W25Q64JV<D> {
    pub fn new(device: D) -> Self {
        Self { device }
    }
}

impl<D: SpiDevice> W25Q64JV<D> {
    pub fn fast_read(
        &mut self,
        offset: u32,
        buf: &mut [u8],
    ) -> Result<(), Error<D::Error>> {
        self.flush()?;

        let offset = offset_to_bytes(offset);
        self.device.transaction(&mut [
            Operation::Write(&[
                command::FAST_READ,
                offset[0],
                offset[1],
                offset[2],
                // This byte is necessary as the chip needs 8 dummy clocks
                // (a byte essentially) to allow the device to set the
                // offset internally.
                //
                // Fast read is needed when running at max. frequency.
                0,
            ]),
            Operation::Read(buf),
        ])?;

        Ok(())
    }

    pub fn page_program(
        &mut self,
        offset: u32,
        buf: &[u8],
    ) -> Result<(), Error<D::Error>> {
        // Flush before assertions is intentional.
        self.flush()?;

        // These are assertions to avoid logic errors, there should never be a
        // case where code using this driver doesn't perform the page program
        // in chunks or where the page offset is not aligned.
        assert!(buf.len() >= 1 && buf.len() <= 256);

        let offset = offset_to_bytes(offset);
        self.device.write(&[command::WRITE_ENABLE])?;
        self.device.transaction(&mut [
            Operation::Write(&[
                command::PAGE_PROGRAM,
                offset[0],
                offset[1],
                offset[2],
            ]),
            Operation::Write(buf),
        ])?;

        Ok(())
    }

    /// Read status register 1.
    pub fn read_status_1(&mut self) -> Result<Status1, Error<D::Error>> {
        let mut result = [0];
        self.device
            .transaction(&mut [
                Operation::Write(&[command::READ_STATUS_REGISTER_1]),
                Operation::Read(&mut result),
            ])
            .map(|_| {
                Status1::from_bits(result[0]).expect("bits should all be known")
            })
            .map_err(Error::from)
    }

    /// Erase a sector.
    pub fn sector_erase(&mut self, offset: u32) -> Result<(), Error<D::Error>> {
        self.flush()?;

        let offset = offset_to_bytes(offset);
        self.device.write(&[command::WRITE_ENABLE])?;
        self.device.write(&[
            command::SECTOR_ERASE,
            offset[0],
            offset[1],
            offset[2],
        ])?;

        Ok(())
    }

    /// Erase a 64 KiB block.
    pub fn block_erase_64kib(
        &mut self,
        offset: u32,
    ) -> Result<(), Error<D::Error>> {
        self.flush()?;

        let offset = offset_to_bytes(offset);
        self.device.write(&[command::WRITE_ENABLE])?;
        self.device.write(&[
            command::BLOCK_ERASE_64KIB,
            offset[0],
            offset[1],
            offset[2],
        ])?;

        Ok(())
    }

    /// Flush the contents of the SPI flash.
    ///
    /// After a read or erase operation on the memory will be busy writing
    /// or erasing the data, this method waits for the memory to finish the
    /// internal operations.
    pub fn flush(&mut self) -> Result<(), Error<D::Error>> {
        // TODO: This should be bounded to avoid a lock up here if the SPI
        // flash malfunctions. Add timeout variable similar to the one in
        // STM32 HAL functions.
        loop {
            let status = self.read_status_1()?;
            if !status.contains(Status1::BUSY) {
                break;
            }
        }

        Ok(())
    }
}

/// Errors that can happend when using the flash.
#[derive(Debug)]
pub enum Error<E> {
    /// The underlying SPI driver returned an error.
    SpiDevice(E),
}

impl<E> From<E> for Error<E> {
    fn from(e: E) -> Self {
        Error::SpiDevice(e)
    }
}

impl<E: Debug> NorFlashError for Error<E> {
    fn kind(&self) -> NorFlashErrorKind {
        match self {
            Error::SpiDevice(_) => NorFlashErrorKind::Other,
        }
    }
}

impl<D: SpiDevice> ErrorType for W25Q64JV<D> {
    type Error = Error<D::Error>;
}

impl<D: SpiDevice> ReadNorFlash for W25Q64JV<D> {
    const READ_SIZE: usize = 1;

    fn read(
        &mut self,
        offset: u32,
        bytes: &mut [u8],
    ) -> Result<(), Self::Error> {
        self.fast_read(offset, bytes)
    }

    fn capacity(&self) -> usize {
        8 * 1024 * 1024
    }
}

impl<D: SpiDevice> NorFlash for W25Q64JV<D> {
    // From Winbond datasheet, they allow from 1 to 256 bytes to be written.
    //
    // (At previously erased locations)
    const WRITE_SIZE: usize = 1;
    const ERASE_SIZE: usize = 4096;

    // TODO: This is not implemented as we don't use this from the main crate
    // to avoid friction with the previous code as that code assumes that we
    // erase sectors and pages.
    fn erase(&mut self, _from: u32, _to: u32) -> Result<(), Self::Error> {
        Ok(())
    }

    // NOTE: Check later if the MicroPython code assumes that we write more
    // than 256 bytes to be written in a single transaction.  The datasheet
    // in theory allows it.
    fn write(&mut self, offset: u32, bytes: &[u8]) -> Result<(), Self::Error> {
        self.page_program(offset, bytes)
    }
}

fn offset_to_bytes(offset: u32) -> [u8; 3] {
    assert!(offset < 1 << 24);

    [
        ((offset >> 16) & 0xFF) as u8,
        ((offset >> 8) & 0xFF) as u8,
        (offset & 0xFF) as u8,
    ]
}
