// SPDX-FileCopyrightText: 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use crate::secp256k1::PRE_ALLOCATED_CTX;
use bitcoin_hashes::sha256d;
use core::{ffi::c_char, slice};
use foundation_firmware::{VerifyHeaderError, VerifySignatureError};
use secp256k1::PublicKey;

pub const VERSION_LEN: usize = 8;

// These are defined here as cbindgen does not support generating C
// definitions for items outside of this crate.
//
// Note: keep in sync. with:
//
//  - ports/stm32/boards/Passport/include/fwheader.h
pub const FIRMWARE_MAGIC_MONO: u32 = 0x50415353;
pub const FIRMWARE_MAGIC_COLOR: u32 = 0x53534150;

/// The result of the firmware update verification.
/// cbindgen:rename-all=ScreamingSnakeCase
/// cbindgen:prefix-with-name
#[repr(C)]
pub enum FirmwareResult {
    // Header.
    /// The firmware validation succeed.
    HeaderOk {
        version: [c_char; VERSION_LEN],
        magic: u32,
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
    /// Missing user public key
    MissingUserPublicKey,
    /// Invalid hash length
    InvalidHashLength,
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
            VerifySignatureError::MissingUserPublicKey => MissingUserPublicKey,
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

    // Developer images use only the first signature. Require the unused
    // second key and signature to be zero in both installer entry points.
    if header.is_signed_by_user() {
        if header.signature.public_key2 != 0 {
            *result = FirmwareResult::InvalidPublicKey2Index {
                index: header.signature.public_key2,
            };
            return None;
        }
        if header.signature.signature2.serialize_compact() != [0; 64] {
            *result = FirmwareResult::InvalidHeader;
            return None;
        }
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
                magic: header.information.magic,
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
    let firmware_hash = match sha256d::Hash::from_slice(hash) {
        Ok(v) => v,
        Err(_) => {
            *result = FirmwareResult::InvalidHashLength;
            return;
        }
    };

    let user_public_key = user_public_key
        .map(|v| {
            let mut buf = [0; 65];
            buf[0] = 0x04;
            (&mut buf[1..]).copy_from_slice(v);
            buf
        })
        .and_then(|v| {
            // If we fail to parse the public key, it means that the user
            // installed an invalid public key to the secure element.
            PublicKey::from_slice(&v).ok()
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
        Err(e) => *result = FirmwareResult::from(e),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use foundation_firmware::{
        Information, HEADER_LEN, MAX_PUBLIC_KEYS, USER_KEY,
    };
    use secp256k1::{Message, SecretKey};

    const KEY1_OFFSET: usize = Information::LEN;
    const SIGNATURE1_OFFSET: usize = KEY1_OFFSET + 4;
    const KEY2_OFFSET: usize = SIGNATURE1_OFFSET + 64;
    const SIGNATURE2_OFFSET: usize = KEY2_OFFSET + 4;

    fn developer_header(magic: u32) -> (Vec<u8>, [u8; 32], [u8; 64]) {
        let info = Information {
            magic,
            timestamp: 1,
            date: "Sep 21, 2026".try_into().unwrap(),
            version: "2.4.0".try_into().unwrap(),
            length: HEADER_LEN,
        };
        let mut header = vec![0; HEADER_LEN as usize];
        header[..Information::LEN].copy_from_slice(&info.serialize());
        header[KEY1_OFFSET..SIGNATURE1_OFFSET]
            .copy_from_slice(&USER_KEY.to_le_bytes());

        // Use a real signature so header mutations cannot be mistaken for a
        // rejection of an otherwise invalid developer signature.
        let hash = [42; 32];
        let key = SecretKey::from_slice(&[1; 32]).unwrap();
        let signature = PRE_ALLOCATED_CTX
            .sign_ecdsa(&Message::from_digest(hash), &key)
            .serialize_compact();
        header[SIGNATURE1_OFFSET..KEY2_OFFSET].copy_from_slice(&signature);
        let mut public_key = [0; 64];
        public_key.copy_from_slice(
            &PublicKey::from_secret_key(&PRE_ALLOCATED_CTX, &key)
                .serialize_uncompressed()[1..],
        );
        (header, hash, public_key)
    }

    fn check_header(header: &[u8]) -> FirmwareResult {
        let mut result = FirmwareResult::InvalidHeader;
        verify_update_header(header.as_ptr(), header.len(), 0, &mut result);
        result
    }

    fn check_signature(
        header: &[u8],
        hash: &[u8; 32],
        key: &[u8; 64],
    ) -> FirmwareResult {
        let mut result = FirmwareResult::InvalidHeader;
        verify_update_signatures(
            header.as_ptr(),
            header.len(),
            0,
            hash,
            Some(key),
            &mut result,
        );
        result
    }

    #[test]
    fn canonical_developer_firmware_requires_valid_signature() {
        for magic in [FIRMWARE_MAGIC_MONO, FIRMWARE_MAGIC_COLOR] {
            let (header, hash, key) = developer_header(magic);
            assert!(matches!(
                check_header(&header),
                FirmwareResult::HeaderOk {
                    signed_by_user: true,
                    ..
                }
            ));
            assert!(matches!(
                check_signature(&header, &hash, &key),
                FirmwareResult::SignaturesOk
            ));
            assert!(matches!(
                check_signature(&header, &[0; 32], &key),
                FirmwareResult::InvalidUserSignature
            ));
        }
    }

    #[test]
    fn installer_rejects_nonzero_developer_second_key() {
        for magic in [FIRMWARE_MAGIC_MONO, FIRMWARE_MAGIC_COLOR] {
            let (mut header, hash, key) = developer_header(magic);
            for index in [1, 2, MAX_PUBLIC_KEYS, u32::MAX] {
                header[KEY2_OFFSET..SIGNATURE2_OFFSET]
                    .copy_from_slice(&index.to_le_bytes());
                for result in [
                    check_header(&header),
                    check_signature(&header, &hash, &key),
                ] {
                    assert!(matches!(result,
                        FirmwareResult::InvalidPublicKey2Index { index: actual } if actual == index));
                }
            }
        }
    }

    #[test]
    fn installer_rejects_nonzero_developer_second_signature() {
        let (header, hash, key) = developer_header(FIRMWARE_MAGIC_COLOR);
        for offset in 0..64 {
            let mut malformed = header.clone();
            malformed[SIGNATURE2_OFFSET + offset] = 1;
            assert!(matches!(
                check_header(&malformed),
                FirmwareResult::InvalidHeader
            ));
            assert!(matches!(
                check_signature(&malformed, &hash, &key),
                FirmwareResult::InvalidHeader
            ));
        }
    }

    #[test]
    fn official_header_may_have_second_key_and_signature() {
        let (mut header, _, _) = developer_header(FIRMWARE_MAGIC_COLOR);
        header[KEY1_OFFSET..SIGNATURE1_OFFSET]
            .copy_from_slice(&0u32.to_le_bytes());
        header[KEY2_OFFSET..SIGNATURE2_OFFSET]
            .copy_from_slice(&1u32.to_le_bytes());
        header.copy_within(SIGNATURE1_OFFSET..KEY2_OFFSET, SIGNATURE2_OFFSET);
        assert!(matches!(
            check_header(&header),
            FirmwareResult::HeaderOk {
                signed_by_user: false,
                ..
            }
        ));
    }

    #[test]
    fn sanity_test() {
        assert_eq!(VERSION_LEN, foundation_firmware::VERSION_LEN);
        assert_eq!(
            FIRMWARE_MAGIC_MONO,
            foundation_firmware::Information::MAGIC_MONO
        );
        assert_eq!(
            FIRMWARE_MAGIC_COLOR,
            foundation_firmware::Information::MAGIC_COLOR
        );
    }
}
