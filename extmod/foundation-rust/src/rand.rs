// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Interface to Passport random number generator.

use core::{ffi::c_void, num::NonZeroU32};

use rand::{CryptoRng, Error, RngCore};

const ERROR_CODE_FATAL: u32 = 1;

/// Passport cryptographically secure random number generator.
///
/// Uses the board's avalanche noise source, the MCU RNG and the
/// hardware RNG.
#[derive(Debug, Clone, Copy)]
pub struct PassportRng;

impl RngCore for PassportRng {
    fn next_u32(&mut self) -> u32 {
        rand_core::impls::next_u32_via_fill(self)
    }

    fn next_u64(&mut self) -> u64 {
        rand_core::impls::next_u64_via_fill(self)
    }

    fn fill_bytes(&mut self, dest: &mut [u8]) {
        self.try_fill_bytes(dest).expect("fatal Passport RNG error");
    }

    fn try_fill_bytes(&mut self, dest: &mut [u8]) -> Result<(), Error> {
        const MIN_LEN: usize = 4;

        // 4 bytes at least are required to fill.
        let mut tmp = [0; 4];
        let (buf, buf_len) = if dest.len() < MIN_LEN {
            (tmp.as_mut_ptr() as *mut c_void, tmp.len())
        } else {
            (dest.as_mut_ptr() as *mut c_void, dest.len())
        };

        unsafe { noise_enable() };
        let succeed =
            unsafe { noise_get_random_bytes(NOISE_ALL, buf, buf_len) };
        if !succeed {
            unsafe { noise_disable() };
            return Err(Error::from(
                NonZeroU32::new(ERROR_CODE_FATAL).unwrap(),
            ));
        }
        unsafe { noise_disable() };

        if dest.len() < MIN_LEN {
            dest.copy_from_slice(&tmp[..dest.len()]);
        }

        Ok(())
    }
}

impl CryptoRng for PassportRng {}

const NOISE_AVALANCHE_SOURCE: u8 = 1 << 0;
const NOISE_MCU_RNG_SOURCE: u8 = 1 << 1;
const NOISE_SE_RNG_SOURCE: u8 = 1 << 2;
const NOISE_ALL: u8 =
    NOISE_AVALANCHE_SOURCE | NOISE_MCU_RNG_SOURCE | NOISE_SE_RNG_SOURCE;

extern "C" {
    fn noise_enable();
    fn noise_disable();
    fn noise_get_random_bytes(
        sources: u8,
        buf: *mut c_void,
        buf_len: usize,
    ) -> bool;
}
