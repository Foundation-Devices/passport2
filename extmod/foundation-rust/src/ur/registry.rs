// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
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
            // NOTE: This is unreachable because the firmware should never
            // create this value as this is only created by Envoy.
            UR_Value::PassportRequest(_) => panic!(
                "Not implemented as it isn't needed. Should be unreachable"
            ),
            UR_Value::PassportResponse(v) => Value::PassportResponse(v.into()),
        }
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
