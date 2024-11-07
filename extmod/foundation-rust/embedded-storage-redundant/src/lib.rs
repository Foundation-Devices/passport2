// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Embedded storage redundant reader.
//!
//! This crate provides a layer to a [`embedded-storage`] NOR flash device to
//! perform multiple redundant reads to the storage device while comparing
//! the contents of each read for consistency.  If the contents don't match
//! then it is retried a certain amount of times before giving up and
//! returning the first buffer.
//!
//! The [`RedundantRead`] structure accepts parameter for the buffer size,
//! number of redundant copies (the quorum).
//!
//! The higher the buffer size and more copies the higher the time to
//! compare the buffers.

#![no_std]

use embedded_storage::nor_flash::{
    ErrorType, NorFlash, NorFlashError, NorFlashErrorKind, ReadNorFlash,
};
use heapless::Vec;

/// Redundant reads layer.
///
/// - `N` is the length of each redundant copy.
/// - `QUORUM` the number of redundant copies.
#[derive(Debug)]
pub struct RedundantRead<S, const N: usize, const QUORUM: usize> {
    storage: S,
    buffers: Vec<Vec<u8, N>, QUORUM>,
    max_read_attempts: usize,
}

impl<S, const N: usize, const QUORUM: usize> RedundantRead<S, N, QUORUM> {
    pub fn new(storage: S, max_read_attempts: usize) -> Self {
        let mut buffers = Vec::new();
        for _ in 0..QUORUM {
            buffers.push(Vec::new()).unwrap();
        }

        Self {
            storage,
            buffers,
            max_read_attempts,
        }
    }

    /// Return the inner storage as a reference.
    pub fn as_inner(&self) -> &S {
        &self.storage
    }

    /// Return the inner storage as a mutable reference.
    pub fn as_mut_inner(&mut self) -> &mut S {
        &mut self.storage
    }
}

/// Errors that can happen while using [`RedundantRead`].
#[derive(Debug)]
pub enum Error<E> {
    /// None of the redundant reads performed matched.
    ///
    /// Data consistency cannot be guaranteed.
    InconsistentBuffers,
    /// A device error.
    Device(E),
}

impl<E> From<E> for Error<E> {
    fn from(error: E) -> Self {
        Self::Device(error)
    }
}

impl<E: NorFlashError> NorFlashError for Error<E> {
    fn kind(&self) -> NorFlashErrorKind {
        match self {
            Error::InconsistentBuffers => NorFlashErrorKind::Other,
            Error::Device(e) => e.kind(),
        }
    }
}

impl<S: ErrorType, const N: usize, const QUORUM: usize> ErrorType
    for RedundantRead<S, N, QUORUM>
{
    type Error = Error<S::Error>;
}

impl<S: ReadNorFlash, const N: usize, const QUORUM: usize> ReadNorFlash
    for RedundantRead<S, N, QUORUM>
{
    const READ_SIZE: usize = S::READ_SIZE;

    fn read(
        &mut self,
        offset: u32,
        bytes: &mut [u8],
    ) -> Result<(), Self::Error> {
        // Read is larger than what we support, just do it without redundancy.
        if bytes.len() >= N {
            return self.storage.read(offset, bytes).map_err(Error::from);
        }

        self.storage.read(offset, bytes)?;

        for i in 0..QUORUM {
            let buffer = &mut self.buffers[i];
            buffer.clear();
            buffer
                .extend_from_slice(bytes)
                .expect("we check previously that bytes < N");
        }

        let mut num_reads = 0;
        let mut current_index = 0;

        loop {
            let mut retry = false;

            let current_buffer = &mut self.buffers[current_index];
            self.storage.read(offset, current_buffer)?;

            // Next index, plus wrap around.
            current_index = (current_index + 1) % QUORUM;
            num_reads += 1;

            if num_reads >= QUORUM {
                for i in 0..QUORUM {
                    if self.buffers[i] != self.buffers[i + 1] {
                        retry = true;
                    }
                }
            }

            if num_reads < QUORUM
                || (retry && num_reads < self.max_read_attempts)
            {
                continue;
            } else {
                // If we need to retry but we exceeded the maximum read
                // attemps then lets return an error.
                if retry {
                    return Err(Error::InconsistentBuffers);
                } else {
                    // Copy the buffer out to the caller. All buffers are equal.
                    bytes.copy_from_slice(&self.buffers[0]);
                    return Ok(());
                }
            }
        }
    }

    fn capacity(&self) -> usize {
        self.storage.capacity()
    }
}

impl<S: NorFlash, const N: usize, const QUORUM: usize> NorFlash
    for RedundantRead<S, N, QUORUM>
{
    const WRITE_SIZE: usize = S::WRITE_SIZE;
    const ERASE_SIZE: usize = S::ERASE_SIZE;

    fn erase(&mut self, from: u32, to: u32) -> Result<(), Self::Error> {
        self.storage.erase(from, to).map_err(Error::from)
    }

    fn write(&mut self, offset: u32, bytes: &[u8]) -> Result<(), Self::Error> {
        self.storage.write(offset, bytes).map_err(Error::from)
    }
}
