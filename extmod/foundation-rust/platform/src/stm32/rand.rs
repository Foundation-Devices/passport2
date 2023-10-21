// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! # Passport random number generator.
//!
//! This implements the interface for usage with [`rand`] to the Passport'so
//! random number generator.

use core::{ffi::c_void, num::NonZeroU32};

use crate::stm32::ffi::{
    noise_disable, noise_enable, noise_get_random_bytes, NOISE_ALL,
};

pub const ERROR_CODE_FATAL: u32 = 1;

/// Constructs a Passport RNG.
pub fn passport_rng() -> PassportRng {
    PassportRng { __private: () }
}

/// Passport cryptographically secure random number generator.
///
/// Uses the board's avalanche noise source, the MCU RNG and the
/// hardware RNG.
///
/// Created with [`passport_rng`].
#[derive(Debug, Clone, Copy)]
pub struct PassportRng {
    __private: (),
}

impl rand_core::RngCore for PassportRng {
    fn next_u32(&mut self) -> u32 {
        rand_core::impls::next_u32_via_fill(self)
    }

    fn next_u64(&mut self) -> u64 {
        rand_core::impls::next_u64_via_fill(self)
    }

    fn fill_bytes(&mut self, dest: &mut [u8]) {
        self.try_fill_bytes(dest).expect("fatal Passport RNG error");
    }

    fn try_fill_bytes(
        &mut self,
        dest: &mut [u8],
    ) -> Result<(), rand_core::Error> {
        const MIN_LEN: usize = 4;

        // 4 bytes at least are required to fill.
        let mut tmp = [0; 4];
        let (buf, buf_len) = if dest.len() < MIN_LEN {
            (tmp.as_mut_ptr() as *mut c_void, tmp.len())
        } else {
            (dest.as_mut_ptr() as *mut c_void, dest.len())
        };

        let succeed = unsafe {
            noise_enable();
            let ret = noise_get_random_bytes(NOISE_ALL, buf, buf_len);
            noise_disable();
            ret
        };

        if !succeed {
            return Err(rand_core::Error::from(
                NonZeroU32::new(ERROR_CODE_FATAL).unwrap(),
            ));
        }

        if dest.len() < MIN_LEN {
            dest.copy_from_slice(&tmp[..dest.len()]);
        }

        Ok(())
    }
}

impl rand_core::CryptoRng for PassportRng {}
