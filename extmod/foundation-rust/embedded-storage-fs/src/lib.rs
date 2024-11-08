// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

//! # `embedded-storage-fs`
//!
//! A `std::fs::File' backed embedded-storage for `std' targets.

use embedded_storage::nor_flash::{
    check_erase, check_read, check_write, ErrorType, NorFlash, NorFlashError,
    NorFlashErrorKind, ReadNorFlash,
};
use std::{
    fs, io,
    io::Read,
    path::{Path, PathBuf},
};

#[derive(Debug)]
pub struct File<
    const READ_SIZE: usize,
    const WRITE_SIZE: usize,
    const ERASE_SIZE: usize,
> {
    path: PathBuf,
    storage: Vec<u8>,
}

#[derive(Debug)]
pub enum Error {
    Io(io::Error),
    InvalidRead(NorFlashErrorKind),
    InvalidErase(NorFlashErrorKind),
    InvalidWrite(NorFlashErrorKind),
}

impl From<io::Error> for Error {
    fn from(e: io::Error) -> Self {
        Self::Io(e)
    }
}

impl NorFlashError for Error {
    fn kind(&self) -> NorFlashErrorKind {
        match self {
            Error::Io(_) => NorFlashErrorKind::Other,
            Error::InvalidRead(kind) => *kind,
            Error::InvalidErase(kind) => *kind,
            Error::InvalidWrite(kind) => *kind,
        }
    }
}

impl<
        const READ_SIZE: usize,
        const WRITE_SIZE: usize,
        const ERASE_SIZE: usize,
    > File<READ_SIZE, WRITE_SIZE, ERASE_SIZE>
{
    pub fn open<P>(path: P, capacity: usize) -> io::Result<Self>
    where
        P: AsRef<Path>,
    {
        let mut file = fs::File::open(&path)?;
        let mut storage = Vec::new();
        file.read_to_end(&mut storage)?;

        // If the file doesn't match the capacity just resize it, it can
        // silently truncate the file or extend it and fill it with blank
        // bytes.
        storage.resize(capacity, 0xFF);

        Ok(Self {
            path: path.as_ref().into(),
            storage,
        })
    }
}

impl<
        const READ_SIZE: usize,
        const WRITE_SIZE: usize,
        const ERASE_SIZE: usize,
    > ErrorType for File<READ_SIZE, WRITE_SIZE, ERASE_SIZE>
{
    type Error = Error;
}

impl<
        const READ_SIZE: usize,
        const WRITE_SIZE: usize,
        const ERASE_SIZE: usize,
    > ReadNorFlash for File<READ_SIZE, WRITE_SIZE, ERASE_SIZE>
{
    const READ_SIZE: usize = READ_SIZE;

    fn read(
        &mut self,
        offset: u32,
        bytes: &mut [u8],
    ) -> Result<(), Self::Error> {
        check_read(&self, offset, bytes.len()).map_err(Error::InvalidRead)?;

        let offset = usize::try_from(offset).expect("u32 bigger than usize");
        bytes.copy_from_slice(&self.storage[offset..offset + bytes.len()]);
        Ok(())
    }

    fn capacity(&self) -> usize {
        self.storage.len()
    }
}

impl<
        const READ_SIZE: usize,
        const WRITE_SIZE: usize,
        const ERASE_SIZE: usize,
    > NorFlash for File<READ_SIZE, WRITE_SIZE, ERASE_SIZE>
{
    const WRITE_SIZE: usize = WRITE_SIZE;
    const ERASE_SIZE: usize = ERASE_SIZE;

    fn erase(&mut self, from: u32, to: u32) -> Result<(), Self::Error> {
        check_erase(&self, from, to).map_err(Error::InvalidErase)?;

        let from = usize::try_from(from).expect("u32 bigger than usize");
        let to = usize::try_from(to).expect("u32 bigger than usize");
        self.storage[from..from + to].fill(0xFF);
        fs::write(&self.path, &self.storage)?;
        Ok(())
    }

    fn write(&mut self, offset: u32, bytes: &[u8]) -> Result<(), Self::Error> {
        check_write(&self, offset, bytes.len()).map_err(Error::InvalidWrite)?;

        let offset = usize::try_from(offset).expect("u32 bigger than usize");
        self.storage[offset..offset + bytes.len()].copy_from_slice(bytes);
        fs::write(&self.path, &self.storage)?;
        Ok(())
    }
}
