// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Decoder.

use core::{slice, str};

use ur::UR;
use ur_foundation::ur;

use crate::ur::{max_fragment_len, registry::UR_Value, UR_Error};

/// Maximum size of an encoded Uniform Resource.
///
/// This value assumes a QR code of version of 16 with ECC L using
/// alphanumeric characters.
pub const UR_DECODER_MAX_STRING: usize = 1408;

/// Maximum sequence count for the decoder.
///
/// Must be a power of two.
pub const UR_DECODER_MAX_SEQUENCE_COUNT: usize = 32;

/// Maximum fragment length.
pub const UR_DECODER_MAX_FRAGMENT_LEN: usize =
    max_fragment_len(UR_DECODER_MAX_STRING);

/// Maximum message length that can be decoded.
pub const UR_DECODER_MAX_MESSAGE_LEN: usize =
    UR_DECODER_MAX_FRAGMENT_LEN * UR_DECODER_MAX_SEQUENCE_COUNT;

/// Maximum number of mixed parts that can be held.
pub const UR_DECODER_MAX_MIXED_PARTS: usize = UR_DECODER_MAX_SEQUENCE_COUNT / 4;

/// Size of the decoder queue.
pub const UR_DECODER_QUEUE_SIZE: usize = 8;

/// Maximum length of the UR type.
/// cbindgen:ignore
pub const UR_DECODER_MAX_UR_TYPE: usize = "crypto-coin-info".len();

/// Statically allocted decoder.
#[no_mangle]
#[used]
#[cfg_attr(dtcm, link_section = ".dtcm")]
pub static mut UR_DECODER: UR_Decoder = UR_Decoder {
    inner: ur::HeaplessDecoder::new_heapless(),
};

/// Uniform Resource decoder.
pub struct UR_Decoder {
    inner: ur::HeaplessDecoder<
        UR_DECODER_MAX_MESSAGE_LEN,
        UR_DECODER_MAX_MIXED_PARTS,
        UR_DECODER_MAX_FRAGMENT_LEN,
        UR_DECODER_MAX_SEQUENCE_COUNT,
        UR_DECODER_QUEUE_SIZE,
        UR_DECODER_MAX_UR_TYPE,
    >,
}

/// Receive an Uniform Resource part.
///
/// # Safety
///
/// - `ur` must point to valid memory and must have a length of `ur_len` bytes.
#[no_mangle]
pub unsafe extern "C" fn ur_decoder_receive(
    decoder: &mut UR_Decoder,
    ur: *const u8,
    ur_len: usize,
    error: &mut UR_Error,
) -> bool {
    // SAFETY: ur and ur_len are assumed to be valid.
    let ur = unsafe { slice::from_raw_parts(ur, ur_len) };

    let result = str::from_utf8(ur)
        .map_err(|e| unsafe { UR_Error::other(&e) })
        .and_then(|ur| {
            UR::parse(ur).map_err(|e| unsafe { UR_Error::other(&e) })
        })
        .and_then(|ur| {
            decoder
                .inner
                .receive(ur)
                .map_err(|e| unsafe { UR_Error::other(&e) })
        });

    match result {
        Ok(_) => true,
        Err(e) => {
            *error = e;
            false
        }
    }
}

/// Returns `true` if the decoder is complete and no more data is needed.
#[no_mangle]
pub extern "C" fn ur_decoder_is_complete(decoder: &mut UR_Decoder) -> bool {
    decoder.inner.is_complete()
}

/// Returns the calculated estimated percentage of completion.
#[no_mangle]
pub extern "C" fn ur_decoder_estimated_percent_complete(
    decoder: &mut UR_Decoder,
) -> u32 {
    (decoder.inner.estimated_percent_complete() * 100.0) as u32
}

/// Clear the decoder in order so a new message can be received.
#[no_mangle]
pub extern "C" fn ur_decoder_clear(decoder: &mut UR_Decoder) {
    decoder.inner.clear();
}

/// Decode the message as an UR value.
#[no_mangle]
pub extern "C" fn ur_decoder_decode_message(
    decoder: &mut UR_Decoder,
    value: &mut UR_Value,
    error: &mut UR_Error,
) -> bool {
    let message = decoder
        .inner
        .message()
        .map_err(|e| unsafe { UR_Error::other(&e) })
        .map(|v| {
            v.ok_or_else(|| unsafe {
                UR_Error::other(&"Decoder still needs more data")
            })
        });

    let message = match message {
        Ok(Ok(v)) => v,
        Err(e) | Ok(Err(e)) => {
            *error = e;
            return false;
        }
    };

    let result = unsafe {
        UR_Value::from_ur(
            decoder
                .inner
                .ur_type()
                .expect("decoder should already contain the UR type"),
            message,
        )
    };
    *value = match result {
        Ok(v) => v,
        Err(e) => {
            *error = e;
            return false;
        }
    };

    true
}

/// Returns `true` if the string is an uniform resource, `false` otherwise.
///
/// # Safety
///
/// - `ur` must point to valid memory and must have a length of `ur_len` bytes.
#[no_mangle]
pub unsafe extern "C" fn ur_validate(ur: *const u8, ur_len: usize) -> bool {
    // SAFETY: ur and ur_len are assumed to be valid.
    let ur = unsafe { slice::from_raw_parts(ur, ur_len) };
    if let Ok(Ok(ur)) = str::from_utf8(ur).map(UR::parse) {
        let bytewords = ur
            .as_bytewords()
            .expect("Parsed URs shouldn't be in a deserialized variant");

        return ur::bytewords::validate(
            bytewords,
            ur::bytewords::Style::Minimal,
        )
        .is_ok();
    }

    false
}
