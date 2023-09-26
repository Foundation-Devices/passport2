// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use embedded_hal::blocking::spi::Transfer;

use crate::ffi::{spi_obj, spi_t, spi_transfer};

#[derive(Debug)]
pub struct Spi(*const spi_t);

impl Spi {
    pub fn from_index(index: usize) -> Self {
        Self(unsafe { &spi_obj[index] as *const _ })
    }
}

impl Transfer<u8> for Spi {
    type Error = core::convert::Infallible;

    fn transfer<'w>(
        &mut self,
        words: &'w mut [u8],
    ) -> Result<&'w [u8], Self::Error> {
        // Approximation of len*8*100/baudrate milliseconds.
        //
        // See ports/stm32/spi.h for more information.
        //
        // FIXME: Use baudrate for the calculation.
        let timeout = words.len() + 100;

        unsafe {
            spi_transfer(
                self.0,
                words.len(),
                words.as_ptr(),
                words.as_mut_ptr(),
                timeout as u32,
            )
        }

        Ok(words)
    }
}
