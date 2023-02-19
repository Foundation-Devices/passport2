// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Uniform Resources.

use core::{ffi::c_char, fmt, fmt::Write};
use ur::fountain::part::Part;
use ur_foundation::ur;

/// cbindgen:ignore
#[used]
#[cfg_attr(sram4, link_section = ".sram4")]
static mut UR_ERROR: heapless::String<256> = heapless::String::new();

pub const fn max_fragment_len(max_characters: usize) -> usize {
    const MAX_UR_PREFIX: usize = "ur:crypto-coin-info/".len()
        + digit_count(u32::MAX as usize)
        + "-".len()
        + digit_count(u32::MAX as usize)
        + "/".len();

    let max_chars_for_part: usize = max_characters - MAX_UR_PREFIX;

    let max_bytes_for_part: usize = (max_chars_for_part / 2) - 4;

    max_bytes_for_part - Part::max_encoded_len()
}

/// Count the number of digits in a number.
pub const fn digit_count(v: usize) -> usize {
    (v.ilog10() + 1) as usize
}

#[repr(C)]
pub enum UR_ErrorKind {
    UR_ERROR_KIND_OTHER,
    UR_ERROR_KIND_UNSUPPORTED,
}

#[repr(C)]
pub struct UR_Error {
    pub kind: UR_ErrorKind,
    pub message: *const c_char,
    pub len: usize,
}

impl UR_Error {
    /// # Safety
    ///
    /// - Single thread assumed.
    /// - Once a new error is created with `new` any `UR_Error` will contain
    /// an invalid message. So the data pointed by `message` should be copied
    /// and `UR_Error` must be dropped.
    pub unsafe fn new(message: &dyn fmt::Display, kind: UR_ErrorKind) -> Self {
        let error = &mut UR_ERROR;
        error.clear();

        if write!(error, "{}", message).is_err() {
            write!(error, "Error is too long to display.")
                .expect("This error string should fit");
        }

        Self {
            kind,
            message: error.as_ptr() as *const c_char,
            len: error.len(),
        }
    }

    /// # Safety
    ///
    /// The same as in [`UR_Error::new`].
    pub unsafe fn other(message: &dyn fmt::Display) -> Self {
        Self::new(message, UR_ErrorKind::UR_ERROR_KIND_OTHER)
    }

    /// # Safety
    ///
    /// The same as in [`UR_Error::new`].
    pub unsafe fn unsupported(message: &dyn fmt::Display) -> Self {
        Self::new(message, UR_ErrorKind::UR_ERROR_KIND_UNSUPPORTED)
    }
}

pub mod decoder;
pub mod encoder;
pub mod registry;

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    fn sanity_test() {
        const fn is_power_of_2(x: usize) -> bool {
            (x & (x - 1)) == 0
        }

        assert!(is_power_of_2(decoder::UR_DECODER_MAX_SEQUENCE_COUNT));
        assert!(is_power_of_2(encoder::UR_ENCODER_MAX_SEQUENCE_COUNT));
        assert!(max_fragment_len(decoder::UR_DECODER_MAX_STRING) > 0);
        assert!(max_fragment_len(encoder::UR_ENCODER_MAX_STRING) > 0);
    }
}
