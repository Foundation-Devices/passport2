// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use core::{ffi::c_char, num::NonZeroU32, slice, str};

use foundation_urtypes::{
    passport::Model,
    registry::PassportRequest,
    registry::{
        CoinInfo, CoinType, DerivedKey, HDKey, Keypath, PassportResponse,
        PathComponents,
    },
    supply_chain_validation::{Challenge, Solution},
    value,
    value::Value,
};
use minicbor::{data::Tag, encode::Write, Encode, Encoder};

use uuid::Uuid;

use crate::ur::UR_Error;

/// `mainnet` network.
pub const UR_NETWORK_MAINNET: u32 = 0;

/// `testnet` network.
pub const UR_NETWORK_TESTNET: u32 = 1;

/// A uniform resource.
#[repr(C)]
pub enum UR_Value {
    /// `bytes`.
    Bytes { data: *const u8, len: usize },
    /// `hdkey`.
    HDKey(UR_HDKey),
    /// `psbt`.
    Psbt { data: *const u8, len: usize },
    /// Passport custom `x-passport-request`.
    PassportRequest(UR_PassportRequest),
    /// Passport custom `x-passport-response`.
    PassportResponse(UR_PassportResponse),
    /// Casa wallet-registration `crypto-account`.
    CryptoAccount(UR_CryptoAccount),
}

impl UR_Value {
    /// # Safety
    ///
    /// Read `UR_Error` safety section as if this function fails this function
    /// will produce an `UR_Error`.
    pub unsafe fn from_ur(
        ur_type: &str,
        message: &[u8],
    ) -> Result<Self, UR_Error> {
        let value = Value::from_ur(ur_type, message).map_err(|e| match e {
            value::Error::UnsupportedResource => UR_Error::unsupported(),
            _ => UR_Error::other(&e),
        })?;

        let value = match value {
            Value::Bytes(bytes) => UR_Value::Bytes {
                data: bytes.as_ptr(),
                len: bytes.len(),
            },
            Value::Psbt(psbt) => UR_Value::Psbt {
                data: psbt.as_ptr(),
                len: psbt.len(),
            },
            Value::PassportRequest(passport_request) => {
                UR_Value::PassportRequest(passport_request.into())
            }
            _ => return Err(UR_Error::unsupported()),
        };

        Ok(value)
    }

    /// # Safety
    ///
    /// Same safety requirements as on [core::slice::from_raw_parts] when the
    /// value is:
    ///
    /// - `UR_Value::Bytes`.
    /// - `UR_Value::Psbt`.
    pub unsafe fn to_value(&self) -> Value<'_> {
        match self {
            UR_Value::Bytes { data, len } => {
                let buf = unsafe { slice::from_raw_parts(*data, *len) };
                Value::Bytes(buf)
            }
            UR_Value::Psbt { data, len } => {
                let buf = unsafe { slice::from_raw_parts(*data, *len) };
                Value::Psbt(buf)
            }
            UR_Value::HDKey(v) => Value::HDKey(v.into()),
            UR_Value::CryptoAccount(_) => panic!(
                "CryptoAccount is encoded directly. Should be unreachable"
            ),
            UR_Value::PassportRequest(_) => panic!(
                "Not implemented as it isn't needed. Should be unreachable"
            ),
            UR_Value::PassportResponse(v) => Value::PassportResponse(v.into()),
        }
    }
}

/// A Casa `crypto-account` containing both supported registration keys.
#[derive(Debug)]
#[repr(C)]
pub struct UR_CryptoAccount {
    pub master_fingerprint: u32,
    pub network: u64,
    pub root_key_data: [u8; 33],
    pub root_chain_code: [u8; 32],
    pub casa_key_data: [u8; 33],
    pub casa_chain_code: [u8; 32],
}

impl UR_CryptoAccount {
    pub const UR_TYPE: &'static str = "crypto-account";

    const TAG_CRYPTO_OUTPUT: Tag = Tag::new(308);
    const TAG_SCRIPT_HASH: Tag = Tag::new(400);
    const TAG_WITNESS_PUBLIC_KEY_HASH: Tag = Tag::new(404);
    const TAG_HDKEY_LEGACY: Tag = Tag::new(303);
    const TAG_KEYPATH_LEGACY: Tag = Tag::new(304);
    const TAG_COIN_INFO_LEGACY: Tag = Tag::new(305);

    fn encode_output<W: Write>(
        &self,
        e: &mut Encoder<W>,
        key_data: &[u8; 33],
        chain_code: &[u8; 32],
        casa_key: bool,
    ) -> Result<(), minicbor::encode::Error<W::Error>> {
        e.tag(Self::TAG_CRYPTO_OUTPUT)?
            .tag(Self::TAG_SCRIPT_HASH)?
            .tag(Self::TAG_WITNESS_PUBLIC_KEY_HASH)?
            .tag(Self::TAG_HDKEY_LEGACY)?
            .map(if casa_key { 5 } else { 4 })?
            .u8(3)?
            .bytes(key_data)?
            .u8(4)?
            .bytes(chain_code)?
            .u8(5)?
            .tag(Self::TAG_COIN_INFO_LEGACY)?;

        if self.network == UR_NETWORK_MAINNET as u64 {
            e.map(0)?;
        } else {
            e.map(1)?.u8(2)?.u64(self.network)?;
        }

        e.u8(6)?.tag(Self::TAG_KEYPATH_LEGACY)?.map(3)?.u8(1)?;
        if casa_key {
            e.array(2)?.u32(45)?.bool(true)?;
        } else {
            e.array(0)?;
        }
        e.u8(2)?
            .u32(self.master_fingerprint)?
            .u8(3)?
            .u8(u8::from(casa_key))?;

        if casa_key {
            e.u8(8)?.u32(self.master_fingerprint)?;
        }

        Ok(())
    }
}

impl<C> Encode<C> for UR_CryptoAccount {
    fn encode<W: Write>(
        &self,
        e: &mut Encoder<W>,
        _ctx: &mut C,
    ) -> Result<(), minicbor::encode::Error<W::Error>> {
        e.map(2)?
            .u8(1)?
            .u32(self.master_fingerprint)?
            .u8(2)?
            .array(2)?;
        self.encode_output(
            e,
            &self.root_key_data,
            &self.root_chain_code,
            false,
        )?;
        self.encode_output(
            e,
            &self.casa_key_data,
            &self.casa_chain_code,
            true,
        )?;
        Ok(())
    }
}

/// A `hdkey`.
#[repr(C)]
pub enum UR_HDKey {
    DerivedKey(UR_DerivedKey),
}

impl<'a> From<&'a UR_HDKey> for HDKey<'a> {
    fn from(value: &'a UR_HDKey) -> HDKey<'a> {
        match value {
            UR_HDKey::DerivedKey(v) => HDKey::DerivedKey(DerivedKey::from(v)),
        }
    }
}

/// Derived `hdkey`.
#[derive(Debug)]
#[repr(C)]
pub struct UR_DerivedKey {
    /// `true` if this is a private key.
    pub is_private: bool,
    /// The key material.
    pub key_data: [u8; 33],
    /// Chain code.
    pub chain_code: [u8; 32],
    /// Whether `chain_code` is present.
    pub has_chain_code: bool,
    /// How the key should be used.
    pub use_info: UR_CoinInfo,
    /// Whether `use_info` is present.
    pub has_use_info: bool,
    /// How the key was derived.
    pub origin: UR_Keypath,
    /// Whether `origin` is present.
    pub has_origin: bool,
    /// The fingerprint of this key's direct ancestor.
    ///
    /// A value of `0` means that the fingerprint is not present.
    pub parent_fingerprint: u32,
}

impl<'a> From<&'a UR_DerivedKey> for DerivedKey<'a> {
    fn from(value: &'a UR_DerivedKey) -> DerivedKey<'a> {
        DerivedKey {
            is_private: value.is_private,
            key_data: value.key_data,
            chain_code: if value.has_chain_code {
                Some(value.chain_code)
            } else {
                None
            },
            use_info: if value.has_use_info {
                Some(CoinInfo::from(&value.use_info))
            } else {
                None
            },
            origin: if value.has_origin {
                Some(Keypath::from(&value.origin))
            } else {
                None
            },
            children: None,
            parent_fingerprint: NonZeroU32::new(value.parent_fingerprint),
            name: None,
            note: None,
        }
    }
}

#[repr(C)]
#[derive(Debug, Clone, Copy)]
pub enum UR_CoinType {
    BTC,
}

impl From<UR_CoinType> for CoinType {
    fn from(v: UR_CoinType) -> CoinType {
        match v {
            UR_CoinType::BTC => CoinType::BTC,
        }
    }
}

#[repr(C)]
#[derive(Debug, Clone)]
pub struct UR_CoinInfo {
    pub coin_type: UR_CoinType,
    pub network: u64,
}

impl From<&UR_CoinInfo> for CoinInfo {
    fn from(v: &UR_CoinInfo) -> CoinInfo {
        CoinInfo {
            coin_type: v.coin_type.into(),
            network: v.network,
        }
    }
}

/// Metadata for the complete or partial derivation path of a key.
#[repr(C)]
#[derive(Debug, Clone)]
pub struct UR_Keypath {
    /// The fingerprint of this key's direct ancestor.
    ///
    /// A value of `0` means that the fingerprint is not present.
    pub source_fingerprint: u32,
    /// How many derivations this key is from the master (which is 0).
    ///
    /// 0 if this is a public key derived directly from a master key.
    pub depth: u8,
    /// Whether `depth` is present.
    pub has_depth: bool,
}

impl<'a> From<Keypath<'a>> for UR_Keypath {
    fn from(v: Keypath<'a>) -> UR_Keypath {
        UR_Keypath {
            source_fingerprint: v
                .source_fingerprint
                .map(|v| v.get())
                .unwrap_or(0),
            depth: v.depth.unwrap_or(0),
            has_depth: v.depth.is_some(),
        }
    }
}

impl<'a> From<&'a UR_Keypath> for Keypath<'a> {
    fn from(v: &UR_Keypath) -> Keypath<'a> {
        Keypath {
            components: PathComponents::from(&[]),
            source_fingerprint: NonZeroU32::new(v.source_fingerprint),
            depth: if v.has_depth { Some(v.depth) } else { None },
        }
    }
}

/// Passport custom `x-passport-request`.
#[repr(C)]
pub struct UR_PassportRequest {
    /// Transaction ID.
    pub transaction_id: [u8; 16],
    /// Supply chain validation challenge.
    pub scv_challenge: UR_Challenge,
    /// Whether SCV challenge is available.
    pub has_scv_challenge: bool,
    /// Request Passport model.
    pub passport_model: bool,
    /// Request Passport firmware version.
    pub passport_firmware_version: bool,
}

impl From<PassportRequest> for UR_PassportRequest {
    fn from(v: PassportRequest) -> UR_PassportRequest {
        let has_scv_challenge = v.scv_challenge.is_some();
        UR_PassportRequest {
            transaction_id: v.transaction_id.into_bytes(),
            scv_challenge: v.scv_challenge.map(UR_Challenge::from).unwrap_or(
                UR_Challenge {
                    id: [0; 32],
                    signature: [0; 64],
                },
            ),
            has_scv_challenge,
            passport_model: v.passport_model,
            passport_firmware_version: v.passport_firmware_version,
        }
    }
}

/// Supply chain validation challenge.
#[repr(C)]
pub struct UR_Challenge {
    /// The ID challenge.
    pub id: [u8; 32],
    /// The signature.
    pub signature: [u8; 64],
}

impl From<Challenge> for UR_Challenge {
    fn from(v: Challenge) -> UR_Challenge {
        UR_Challenge {
            id: v.id,
            signature: v.signature,
        }
    }
}

/// Passport custom `x-passport-response`.
#[repr(C)]
pub struct UR_PassportResponse {
    /// Transaction ID.
    pub transaction_id: [u8; 16],
    /// Supply chain validation challenge.
    pub scv_solution: UR_Solution,
    /// Whether `scv_solution` is present.
    pub has_scv_solution: bool,
    /// Passport model.
    pub passport_model: UR_PassportModel,
    /// Whether `passport_model` present.
    pub has_passport_model: bool,
    /// Passport firmware version.
    pub passport_firmware_version: *const c_char,
    /// Passport firmware version length.
    pub passport_firmware_version_len: usize,
    /// Whether `passport_model` present.
    pub has_passport_firmware_version: bool,
}

impl<'a> From<&'a UR_PassportResponse> for PassportResponse<'a> {
    fn from(v: &'a UR_PassportResponse) -> PassportResponse<'a> {
        PassportResponse {
            transaction_id: Uuid::from_bytes(v.transaction_id),
            scv_solution: if v.has_scv_solution {
                Some((&v.scv_solution).into())
            } else {
                None
            },
            passport_model: if v.has_passport_model {
                Some(v.passport_model.into())
            } else {
                None
            },
            passport_firmware_version: if v.has_passport_firmware_version {
                Some(unsafe {
                    str::from_utf8_unchecked(slice::from_raw_parts(
                        v.passport_firmware_version as *const u8,
                        v.passport_firmware_version_len,
                    ))
                })
            } else {
                None
            },
        }
    }
}

/// Supply Chain Validation solution.
#[repr(C)]
#[derive(Clone)]
pub struct UR_Solution {
    pub word1: *const c_char,
    pub word1_len: usize,

    pub word2: *const c_char,
    pub word2_len: usize,

    pub word3: *const c_char,
    pub word3_len: usize,

    pub word4: *const c_char,
    pub word4_len: usize,
}

impl<'a> From<&'a UR_Solution> for Solution<'a> {
    fn from(v: &'a UR_Solution) -> Solution<'a> {
        Solution {
            word1: unsafe {
                str::from_utf8_unchecked(slice::from_raw_parts(
                    v.word1 as *const u8,
                    v.word1_len,
                ))
            },
            word2: unsafe {
                str::from_utf8_unchecked(slice::from_raw_parts(
                    v.word2 as *const u8,
                    v.word2_len,
                ))
            },
            word3: unsafe {
                str::from_utf8_unchecked(slice::from_raw_parts(
                    v.word3 as *const u8,
                    v.word3_len,
                ))
            },
            word4: unsafe {
                str::from_utf8_unchecked(slice::from_raw_parts(
                    v.word4 as *const u8,
                    v.word4_len,
                ))
            },
        }
    }
}

/// Passport model.
#[derive(Debug, Clone, Copy)]
#[repr(C)]
pub enum UR_PassportModel {
    /// Founders Edition.
    PASSPORT_MODEL_FOUNDERS_EDITION,
    /// Batch 2.
    PASSPORT_MODEL_BATCH2,
}

impl From<UR_PassportModel> for Model {
    fn from(v: UR_PassportModel) -> Model {
        match v {
            UR_PassportModel::PASSPORT_MODEL_FOUNDERS_EDITION => {
                Model::FoundersEdition
            }
            UR_PassportModel::PASSPORT_MODEL_BATCH2 => Model::Batch2,
        }
    }
}

/// Create a new `bytes` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_bytes(
    value: &mut UR_Value,
    data: *mut u8,
    len: usize,
) {
    *value = UR_Value::Bytes { data, len };
}

/// Create a new derived `hdkey` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_derived_key(
    value: &mut UR_Value,
    is_private: bool,
    key_data: &[u8; 33],
    chain_code: Option<&[u8; 32]>,
    use_info: Option<&UR_CoinInfo>,
    origin: Option<&UR_Keypath>,
    parent_fingerprint: u32,
) {
    *value = UR_Value::HDKey(UR_HDKey::DerivedKey(UR_DerivedKey {
        is_private,
        key_data: *key_data,
        chain_code: chain_code.copied().unwrap_or([0u8; 32]),
        has_chain_code: chain_code.is_some(),
        use_info: use_info.cloned().unwrap_or(UR_CoinInfo {
            coin_type: UR_CoinType::BTC,
            network: 0,
        }),
        has_use_info: use_info.is_some(),
        origin: origin.cloned().unwrap_or(UR_Keypath {
            source_fingerprint: 0,
            depth: 0,
            has_depth: false,
        }),
        has_origin: origin.is_some(),
        parent_fingerprint,
    }));
}

/// Create the Casa wallet-registration `crypto-account` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_crypto_account(
    value: &mut UR_Value,
    root_key_data: &[u8; 33],
    root_chain_code: &[u8; 32],
    casa_key_data: &[u8; 33],
    casa_chain_code: &[u8; 32],
    master_fingerprint: u32,
    network: u64,
) {
    *value = UR_Value::CryptoAccount(UR_CryptoAccount {
        master_fingerprint,
        network,
        root_key_data: *root_key_data,
        root_chain_code: *root_chain_code,
        casa_key_data: *casa_key_data,
        casa_chain_code: *casa_chain_code,
    });
}

/// Create a new `psbt` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_psbt(
    value: &mut UR_Value,
    data: *mut u8,
    len: usize,
) {
    *value = UR_Value::Psbt { data, len };
}

/// Create a new Passport custom `x-passport-response` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_passport_response(
    value: &mut UR_Value,
    transaction_id: &[u8; 16],
    solution: &UR_Solution,
    passport_model: UR_PassportModel,
    passport_firmware_version: *const c_char,
    passport_firmware_version_len: usize,
) {
    *value = UR_Value::PassportResponse(UR_PassportResponse {
        transaction_id: *transaction_id,
        scv_solution: solution.clone(),
        has_scv_solution: true,
        passport_model,
        has_passport_model: true,
        passport_firmware_version,
        passport_firmware_version_len,
        has_passport_firmware_version: true,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use minicbor::encode::write::Cursor;

    #[test]
    fn casa_crypto_account_wire_format_is_pinned() {
        let account = UR_CryptoAccount {
            master_fingerprint: 0x1234_5678,
            network: UR_NETWORK_MAINNET as u64,
            root_key_data: [2; 33],
            root_chain_code: [3; 32],
            casa_key_data: [4; 33],
            casa_chain_code: [5; 32],
        };
        let mut output = Cursor::new([0u8; 256]);
        account
            .encode(&mut Encoder::new(&mut output), &mut ())
            .unwrap();

        let expected = concat!(
            "a2011a123456780282d90134d90190d90194d9012fa40358210202020202020202020202020202020202020202",
            "020202020202020202020202020458200303030303030303030303030303030303030303030303030303030303",
            "03030305d90131a006d90130a30180021a123456780300d90134d90190d90194d9012fa5035821040404040404",
            "040404040404040404040404040404040404040404040404040404045820050505050505050505050505050505",
            "050505050505050505050505050505050505d90131a006d90130a30182182df5021a123456780301081a123456",
            "78",
        );
        let encoded = &output.get_ref()[..output.position()];
        assert_eq!(encoded.len() * 2, expected.len());
        for (actual, expected) in
            encoded.iter().zip(expected.as_bytes().chunks_exact(2))
        {
            let nibble = |byte| match byte {
                b'0'..=b'9' => byte - b'0',
                b'a'..=b'f' => byte - b'a' + 10,
                _ => unreachable!(),
            };
            assert_eq!(*actual, nibble(expected[0]) << 4 | nibble(expected[1]));
        }
    }
}
