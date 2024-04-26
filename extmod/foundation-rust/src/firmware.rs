// SPDX-FileCopyrightText: 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use crate::secp256k1::PRE_ALLOCATED_CTX;
use bitcoin_hashes::{sha256d, Hash};
use core::{ffi::c_char, slice};
use foundation_firmware::{VerifyHeaderError, VerifySignatureError};
use secp256k1::PublicKey;

pub const VERSION_LEN: usize = 8;

/// The result of the firmware update verification.
/// cbindgen:rename-all=ScreamingSnakeCase
/// cbindgen:prefix-with-name
#[repr(C)]
pub enum FirmwareResult {
    // Header.
    /// The firmware validation succeed.
    HeaderOk {
        version: [c_char; VERSION_LEN],
        signed_by_user: bool,
    },
    /// The header format is not valid.
    InvalidHeader,
    /// Unknown magic number.
    UnknownMagic { magic: u32 },
    /// The timestamp field is invalid.
    InvalidTimestamp,
    /// The firmware is too small.
    TooSmall { len: u32 },
    /// The firmware is too big.
    TooBig { len: u32 },
    /// The firmware is older than the current firmware.
    TooOld {
        timestamp: u32,
        // version: *const c_char,
    },
    /// Public Key 1 is out of range.
    InvalidPublicKey1Index { index: u32 },
    /// Public Key 2 is out of range.
    InvalidPublicKey2Index { index: u32 },
    /// The same public key was used for the two signatures.
    SamePublicKey {
        /// Index of the duplicated key.
        index: u32,
    },
    // Signatures.
    /// Signature verification succeed.
    SignaturesOk,
    /// The user signed firmware is not valid.
    InvalidUserSignature,
    /// The first signature verification failed.
    FailedSignature1,
    /// The second signature verification failed.
    FailedSignature2,
}

impl From<VerifyHeaderError> for FirmwareResult {
    fn from(e: VerifyHeaderError) -> Self {
        use FirmwareResult::*;

        match e {
            VerifyHeaderError::UnknownMagic(magic) => UnknownMagic { magic },
            VerifyHeaderError::InvalidTimestamp => InvalidTimestamp,
            VerifyHeaderError::FirmwareTooSmall(len) => TooSmall { len },
            VerifyHeaderError::FirmwareTooBig(len) => TooBig { len },
            VerifyHeaderError::InvalidPublicKey1Index(index) => {
                InvalidPublicKey1Index { index }
            }
            VerifyHeaderError::InvalidPublicKey2Index(index) => {
                InvalidPublicKey2Index { index }
            }
            VerifyHeaderError::SamePublicKeys(index) => SamePublicKey { index },
        }
    }
}

impl From<VerifySignatureError> for FirmwareResult {
    fn from(e: VerifySignatureError) -> Self {
        use FirmwareResult::*;

        match e {
            VerifySignatureError::InvalidUserSignature { .. } => {
                InvalidUserSignature
            }
            VerifySignatureError::FailedSignature1 { .. } => FailedSignature1,
            VerifySignatureError::FailedSignature2 { .. } => FailedSignature2,
            // No need to implement this, see comment on
            // verify_update_signatures.
            VerifySignatureError::MissingUserPublicKey => unimplemented!(),
        }
    }
}

fn verify_update_header_impl(
    header: &[u8],
    current_timestamp: u32,
    result: &mut FirmwareResult,
) -> Option<foundation_firmware::Header> {
    let header = match foundation_firmware::header(header) {
        Ok((_, header)) => header,
        Err(_) => {
            *result = FirmwareResult::InvalidHeader;
            return None;
        }
    };

    if let Err(e) = header.verify() {
        *result = FirmwareResult::from(e);
        return None;
    }

    if header.information.timestamp < current_timestamp {
        *result = FirmwareResult::TooOld {
            timestamp: header.information.timestamp,
        };
        return None;
    }

    Some(header)
}

/// Verify the header of a firmware update.
#[export_name = "foundation_firmware_verify_update_header"]
pub extern "C" fn verify_update_header(
    header: *const u8,
    header_len: usize,
    current_timestamp: u32,
    result: &mut FirmwareResult,
) {
    let header = unsafe { slice::from_raw_parts(header, header_len) };

    match verify_update_header_impl(header, current_timestamp, result) {
        Some(header) => {
            let version_bytes = header.information.version.as_bytes();
            let mut version = [0; VERSION_LEN];
            for (i, &b) in version_bytes.iter().enumerate() {
                version[i] = b as c_char;
            }
            version[version_bytes.len()] = b'\0' as c_char;

            *result = FirmwareResult::HeaderOk {
                version,
                signed_by_user: header.is_signed_by_user(),
            };
        }
        // Verification failed.
        None => (),
    }
}

#[export_name = "foundation_firmware_verify_update_signatures"]
pub extern "C" fn verify_update_signatures(
    header: *const u8,
    header_len: usize,
    current_timestamp: u32,
    hash: &[u8; 32],
    user_public_key: Option<&[u8; 64]>,
    result: &mut FirmwareResult,
) {
    let header = unsafe { slice::from_raw_parts(header, header_len) };
    let firmware_hash = sha256d::Hash::from_slice(hash)
        .expect("hash should be of correct length");

    let user_public_key = user_public_key
        .map(|v| {
            let mut buf = [0; 65];
            buf[0] = 0x04;
            (&mut buf[1..]).copy_from_slice(v);
            buf
        })
        .map(|v| {
            PublicKey::from_slice(&v).expect("user public key should be valid")
        });

    let header =
        match verify_update_header_impl(header, current_timestamp, result) {
            Some(header) => header,
            None => return,
        };

    match foundation_firmware::verify_signature(
        &PRE_ALLOCATED_CTX,
        &header,
        &firmware_hash,
        user_public_key.as_ref(),
    ) {
        Ok(()) => {
            *result = FirmwareResult::SignaturesOk;
        }
        // The code calling this function must make sure that there's an user
        // public key provided to us before verifying signatures.
        //
        // When verifying signatures is because we are committed to the
        // update, i.e. the user has accepted to do it, so we must have
        // presented an error if there was not an user public key earlier.
        Err(VerifySignatureError::MissingUserPublicKey) => {
            unreachable!("we always provide a user public key")
        }
        Err(e) => *result = FirmwareResult::from(e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sanity_test() {
        assert_eq!(VERSION_LEN, foundation_firmware::VERSION_LEN);
    }
}
