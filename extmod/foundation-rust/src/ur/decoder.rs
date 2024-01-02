// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Decoder.

use core::{fmt, slice, str};

use foundation_ur::{
    bytewords, bytewords::Style, decoder::Error, max_fragment_len,
    HeaplessDecoder, UR,
};

use crate::ur::{max_message_len, registry::UR_Value, UR_Error, UR_MAX_TYPE};

/// Maximum size of an encoded Uniform Resource.
///
/// This value assumes a QR code of version of 16 with ECC L using
/// alphanumeric characters.
pub const UR_DECODER_MAX_STRING: usize = 1408;

/// Maximum sequence count for the decoder.
///
/// Must be a power of two.
pub const UR_DECODER_MAX_SEQUENCE_COUNT: usize = 128;

/// Maximum fragment length.
pub const UR_DECODER_MAX_FRAGMENT_LEN: usize =
    max_fragment_len(UR_MAX_TYPE, usize::MAX, UR_DECODER_MAX_STRING);

/// Maximum message length that can be decoded.
pub const UR_DECODER_MAX_MESSAGE_LEN: usize = 24 * 1024;

/// Maximum message length for a single part UR.
pub const UR_DECODER_MAX_SINGLE_PART_MESSAGE_LEN: usize =
    max_message_len(UR_DECODER_MAX_STRING);

/// Maximum number of mixed parts that can be held.
pub const UR_DECODER_MAX_MIXED_PARTS: usize = 8;

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
    inner: HeaplessDecoder::new(),
};

/// cbindgen:ignore
#[used]
#[cfg_attr(dtcm, link_section = ".dtcm")]
static mut UR_DECODER_SINGLE_PART_MESSAGE: heapless::Vec<
    u8,
    UR_DECODER_MAX_SINGLE_PART_MESSAGE_LEN,
> = heapless::Vec::new();

/// Uniform Resource decoder.
pub struct UR_Decoder {
    inner: HeaplessDecoder<
        UR_DECODER_MAX_MESSAGE_LEN,
        UR_DECODER_MAX_MIXED_PARTS,
        UR_DECODER_MAX_FRAGMENT_LEN,
        UR_DECODER_MAX_SEQUENCE_COUNT,
        UR_DECODER_QUEUE_SIZE,
        UR_DECODER_MAX_UR_TYPE,
    >,
}

/// Receive a Uniform Resource part.
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
    num_frames: &mut u32,
) -> bool {
    // SAFETY: ur and ur_len are assumed to be valid.
    let ur = unsafe { slice::from_raw_parts(ur, ur_len) };

    let result = str::from_utf8(ur)
        .map_err(|e| unsafe { UR_Error::other(&e) })
        .and_then(|ur| {
            UR::parse(ur).map_err(|e| unsafe { UR_Error::other(&e) })
        })
        .and_then(|ur| match ur.sequence_count() {
            Some(n) if n > UR_DECODER_MAX_SEQUENCE_COUNT as u32 => {
                Err(unsafe {
                    UR_Error::other(&TooManySequences { sequence_count: n })
                })
            }
            _ => Ok(ur),
        });

    let ur = match result {
        Ok(ur) => ur,
        Err(e) => {
            *error = e;
            return false;
        }
    };

    *num_frames = ur.sequence_count().unwrap_or(0);

    let result = decoder.inner.receive(ur).map_err(|e| match e {
        Error::NotMultiPart => unsafe {
            UR_Error::new(&e, super::UR_ErrorKind::UR_ERROR_KIND_NOT_MULTI_PART)
        },
        _ => unsafe { UR_Error::other(&e) },
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

/// Returns `true` if the decoder doesn't contain any data.
#[no_mangle]
pub extern "C" fn ur_decoder_is_empty(decoder: &mut UR_Decoder) -> bool {
    decoder.inner.is_empty()
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

/// Returns `true` if the string is a uniform resource, `false` otherwise.
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

        return bytewords::validate(bytewords, Style::Minimal).is_ok();
    }

    false
}

/// # Safety
///
/// Same as in `ur_decoder_decode_message`
#[no_mangle]
pub unsafe extern "C" fn ur_decode_single_part(
    ur: *const u8,
    ur_len: usize,
    value: &mut UR_Value,
    error: &mut UR_Error,
) -> bool {
    // SAFETY: ur and ur_len are assumed to be valid.
    let ur = unsafe { slice::from_raw_parts(ur, ur_len) };

    let result = str::from_utf8(ur)
        .map_err(|e| unsafe { UR_Error::other(&e) })
        .and_then(|ur| {
            UR::parse(ur).map_err(|e| unsafe { UR_Error::other(&e) })
        });

    let ur = match result {
        Ok(ur) => ur,
        Err(e) => {
            *error = e;
            return false;
        }
    };

    let message = unsafe { &mut UR_DECODER_SINGLE_PART_MESSAGE };
    message.clear();
    message
        .resize(UR_DECODER_MAX_SINGLE_PART_MESSAGE_LEN, 0)
        .expect("Message buffer should have the same size as in the constant");

    let result = bytewords::decode_to_slice(
        ur.as_bytewords()
            .expect("Uniform Resource should contain bytewords"),
        message,
        Style::Minimal,
    )
    .map_err(|e| unsafe { UR_Error::other(&e) });

    match result {
        Ok(len) => message.truncate(len),
        Err(e) => {
            *error = e;
            return false;
        }
    }

    let result = unsafe { UR_Value::from_ur(ur.as_type(), message) };

    *value = match result {
        Ok(v) => v,
        Err(e) => {
            *error = e;
            return false;
        }
    };

    true
}

struct TooManySequences {
    sequence_count: u32,
}

impl fmt::Display for TooManySequences {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        write!(
            f,
            "The UR contains more sequences than we can handle.\n\nMaximum sequence count supported: {}.\n\nMessage sequence count: {}.",
            UR_DECODER_MAX_SEQUENCE_COUNT,
            self.sequence_count,
        )
    }
}
