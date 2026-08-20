// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Encoder.

use core::{ffi::c_char, fmt::Write, ptr, slice, str};

use foundation_ur::{max_fragment_len, HeaplessEncoder};
use minicbor::{Encode, Encoder};

use crate::ur::{
    decoder::UR_DECODER_MAX_MESSAGE_LEN, registry::UR_Value, UR_MAX_TYPE,
};

/// Maximum size of an encoded Uniform Resource.
///
/// This value assumes a QR code of version of 12 with ECC L using
/// alphanumeric characters.
pub const UR_ENCODER_MAX_STRING: usize = 535;

/// Minimum size of an encoded Uniform Resource.
///
/// This value assumes a QR code of version of 7 with ECC L using
/// alphanumeric characters.
pub const UR_ENCODER_MIN_STRING: usize = 224;

/// Maximum fragment length.
///
/// This is the maximum fragment length in bytes, this is not for the
/// CBOR encoding or bytewords encoding but one of the equally sized
/// parts that the message is divided into.
/// cbindgen:ignore
pub const UR_ENCODER_MAX_FRAGMENT_LEN: usize =
    max_fragment_len(UR_MAX_TYPE, usize::MAX, UR_ENCODER_MAX_STRING);

/// Minimum fragment length.
pub const UR_ENCODER_MIN_FRAGMENT_LEN: usize =
    max_fragment_len(UR_MAX_TYPE, usize::MAX, UR_ENCODER_MIN_STRING);

/// Maximum sequence count for the decoder.
///
/// Must be a power of two.
/// cbindgen:ignore
pub const UR_ENCODER_MAX_SEQUENCE_COUNT: usize = usize::next_power_of_two(
    UR_DECODER_MAX_MESSAGE_LEN / UR_ENCODER_MIN_FRAGMENT_LEN,
);

/// Maximum message length that can be encoded.
/// cbindgen:ignore
pub const UR_ENCODER_MAX_MESSAGE_LEN: usize = UR_DECODER_MAX_MESSAGE_LEN;

/// Statically allocated encoder.
#[no_mangle]
#[used]
#[cfg_attr(dtcm, link_section = ".dtcm")]
pub static mut UR_ENCODER: UR_Encoder = UR_Encoder {
    inner: HeaplessEncoder::new(),
};

/// cbindgen:ignore
#[used]
#[cfg_attr(sram4, link_section = ".sram4")]
static mut UR_ENCODER_STRING: heapless::Vec<u8, UR_ENCODER_MAX_STRING> =
    heapless::Vec::new();

/// cbindgen:ignore
#[used]
#[cfg_attr(sram4, link_section = ".sram4")]
static mut UR_ENCODER_MESSAGE: heapless::Vec<u8, UR_ENCODER_MAX_MESSAGE_LEN> =
    heapless::Vec::new();

/// cbindgen:ignore
#[used]
#[cfg_attr(sram4, link_section = ".sram4")]
static mut UR_ENCODER_TYPE: heapless::String<{ UR_MAX_TYPE.len() }> =
    heapless::String::new();

/// Uniform Resource encoder.
pub struct UR_Encoder {
    inner: HeaplessEncoder<
        'static,
        'static,
        UR_ENCODER_MAX_FRAGMENT_LEN,
        UR_ENCODER_MAX_SEQUENCE_COUNT,
    >,
}

/// Start the encoder.
///
/// # Parameters
///
/// - `value` is the uniform resource to encode.
/// - `max_chars` is the maximum fragment length in bytes.
///
/// # Safety
///
/// If the `UR_Value` is of type `Bytes` then the pointer must be a valid value
/// and its length too.
///
/// This function assumes that is called on the same thread and its not used
/// concurrently.
#[no_mangle]
pub unsafe extern "C" fn ur_encoder_start(
    encoder: &mut UR_Encoder,
    value: &UR_Value,
    max_chars: usize,
) {
    // SAFETY: The UR_Value can contain some raw pointers which need to be
    // accessed in order to convert it to a `ur::registry::BaseValue` which
    // is then encoded below, so the pointers lifetime only need to be valid
    // for the scope of this function.
    let value = unsafe { value.to_value() };

    // SAFETY: This code assumes that runs on a single thread.
    let message = unsafe { &mut *ptr::addr_of_mut!(UR_ENCODER_MESSAGE) };

    message.clear();
    let mut e = Encoder::new(Writer(message));
    value.encode(&mut e, &mut ()).expect("Couldn't encode UR");

    encoder.inner.start(
        value.ur_type(),
        message,
        max_fragment_len(UR_MAX_TYPE, usize::MAX, max_chars),
    );
}

/// Start the encoder with an already CBOR-encoded Uniform Resource.
///
/// # Safety
///
/// `ur_type` and `message` must be valid for reads of their respective
/// lengths for the duration of this call.
#[no_mangle]
pub unsafe extern "C" fn ur_encoder_start_raw(
    encoder: &mut UR_Encoder,
    ur_type: *const u8,
    ur_type_len: usize,
    message: *const u8,
    message_len: usize,
    max_chars: usize,
) -> bool {
    let ur_type = unsafe { slice::from_raw_parts(ur_type, ur_type_len) };
    let message = unsafe { slice::from_raw_parts(message, message_len) };

    let Ok(ur_type) = str::from_utf8(ur_type) else {
        return false;
    };
    if ur_type.is_empty()
        || ur_type.len() > UR_MAX_TYPE.len()
        || !ur_type
            .bytes()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
    {
        return false;
    }

    let encoder_type = unsafe { &mut *ptr::addr_of_mut!(UR_ENCODER_TYPE) };
    encoder_type.clear();
    if encoder_type.push_str(ur_type).is_err() {
        return false;
    }

    let encoder_message =
        unsafe { &mut *ptr::addr_of_mut!(UR_ENCODER_MESSAGE) };
    encoder_message.clear();
    if encoder_message.extend_from_slice(message).is_err() {
        return false;
    }

    encoder.inner.start(
        encoder_type.as_str(),
        encoder_message,
        max_fragment_len(UR_MAX_TYPE, usize::MAX, max_chars),
    );
    true
}

/// Returns the UR corresponding to the next fountain encoded part.
///
/// # Safety
///
/// This function must not be called if `ur_encoder_start` was not called to
/// start the encoder. Or if the data used to start the encoder is freed.
///
/// # Return Value
///
/// The return value is a NULL terminated string encoded using an uppercase
/// alphabet and using only the characters allowed in QR code alphanumeric
/// mode.
///
/// The pointer is valid until `ur_encoder_next_part` or `ur_encoder_start`
/// are called.
#[no_mangle]
pub unsafe extern "C" fn ur_encoder_next_part(
    encoder: &mut UR_Encoder,
    ur: *mut *const c_char,
    ur_len: *mut usize,
) {
    let part = encoder.inner.next_part();

    let buf = unsafe { &mut *ptr::addr_of_mut!(UR_ENCODER_STRING) };
    buf.clear();
    write!(buf, "{part}").unwrap();
    buf.push(b'\0').unwrap();

    *ur = buf.as_ptr() as *const c_char;
    *ur_len = buf.len() - 1;
}

struct Writer<'a, const N: usize>(&'a mut heapless::Vec<u8, N>);

impl<'a, const N: usize> minicbor::encode::Write for Writer<'a, N> {
    type Error = EndOfSlice;

    fn write_all(&mut self, buf: &[u8]) -> Result<(), Self::Error> {
        self.0.extend_from_slice(buf).map_err(|_| EndOfSlice)
    }
}

#[derive(Debug)]
struct EndOfSlice;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn raw_encoder_preserves_the_ur_type() {
        let ur_type = b"crypto-hdkey";
        let message = b"\xa0";

        unsafe {
            let encoder = &mut *ptr::addr_of_mut!(UR_ENCODER);
            assert!(ur_encoder_start_raw(
                encoder,
                ur_type.as_ptr(),
                ur_type.len(),
                message.as_ptr(),
                message.len(),
                UR_ENCODER_MAX_STRING,
            ));

            let mut encoded = ptr::null();
            let mut encoded_len = 0;
            ur_encoder_next_part(encoder, &mut encoded, &mut encoded_len);
            let encoded =
                slice::from_raw_parts(encoded as *const u8, encoded_len);
            assert!(encoded.starts_with(b"ur:crypto-hdkey/"));
        }
    }
}
