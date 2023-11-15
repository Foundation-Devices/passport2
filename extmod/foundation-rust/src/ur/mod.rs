// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Uniform Resources.

use core::{ffi::c_char, fmt, fmt::Write};

/// cbindgen:ignore
#[used]
#[cfg_attr(sram4, link_section = ".sram4")]
static mut UR_ERROR: heapless::String<256> = heapless::String::new();

/// The maximum length of a UR type that will be accepted or produced.
/// cbindgen:ignore
const UR_MAX_TYPE: &str = "crypto-coin-info";

/// The minimum length of a UR type
/// cbindgen:ignore
const UR_MIN_TYPE: &str = "bytes";

const fn max_message_len(max_characters: usize) -> usize {
    const MAX_UR_PREFIX: usize = "ur:".len() + UR_MAX_TYPE.len();

    let max_chars_for_message = max_characters.saturating_sub(MAX_UR_PREFIX);
    (max_chars_for_message / 2).saturating_sub(4)
}

#[repr(C)]
pub enum UR_ErrorKind {
    UR_ERROR_KIND_OTHER,
    UR_ERROR_KIND_UNSUPPORTED,
    UR_ERROR_KIND_NOT_MULTI_PART,
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

    use crate::ur::decoder::UR_DECODER_MAX_FRAGMENT_LEN;
    use crate::ur::encoder::{
        UR_ENCODER_MAX_FRAGMENT_LEN, UR_ENCODER_MIN_FRAGMENT_LEN,
    };

    #[test]
    fn sanity_test() {
        const fn is_power_of_2(x: usize) -> bool {
            (x & (x - 1)) == 0
        }

        assert!(is_power_of_2(decoder::UR_DECODER_MAX_SEQUENCE_COUNT));
        assert!(is_power_of_2(encoder::UR_ENCODER_MAX_SEQUENCE_COUNT));

        assert_ne!(UR_DECODER_MAX_FRAGMENT_LEN, 0);

        assert_ne!(UR_ENCODER_MIN_FRAGMENT_LEN, 0);
        assert_ne!(UR_ENCODER_MAX_FRAGMENT_LEN, 0);
    }
}
