// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use foundation_bip32::{ChainCode, Fingerprint};
use secp256k1::SecretKey;

/// A extended private key.
#[repr(C)]
pub struct Xpriv {
    pub version: [u8; 4],
    pub depth: u8,
    pub parent_fingerprint: [u8; 4],
    pub child_number: u32,
    pub chain_code: [u8; 32],
    pub private_key: [u8; 32],
}

impl<'a> TryFrom<&'a Xpriv> for foundation_bip32::Xpriv {
    type Error = secp256k1::Error;

    fn try_from(xpriv: &'a Xpriv) -> Result<Self, Self::Error> {
        Ok(Self {
            version: xpriv.version,
            depth: xpriv.depth,
            parent_fingerprint: Fingerprint(xpriv.parent_fingerprint),
            child_number: xpriv.child_number,
            chain_code: ChainCode(xpriv.chain_code),
            private_key: SecretKey::from_byte_array(&xpriv.private_key)?,
        })
    }
}
