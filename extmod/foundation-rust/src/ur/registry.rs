// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use crate::ur::UR_Error;
use core::{ffi::c_char, num::NonZeroU32, slice, str};
use ur::registry::{
    crypto_hdkey::{
        BaseHDKey, CoinType, CryptoCoinInfo, CryptoKeypath, DerivedKey,
        PathComponent,
    },
    crypto_request::Empty,
    BaseValue,
};
use ur_foundation::{
    passport::Model,
    registry::passport::{PassportRequest, PassportResponse},
    supply_chain_validation::{Challenge, Solution},
    ur,
};
use uuid::Uuid;

/// `mainnet` network.
pub const UR_NETWORK_MAINNET: u32 = 0;

/// `testnet` network.
pub const UR_NETWORK_TESTNET: u32 = 1;

/// Maximum number of components that a `crypto-keypath` can have.
pub const UR_MAX_PATH_COMPONENTS: usize = 4;

/// cbindgen:ignore
type PathComponents = heapless::Vec<PathComponent, UR_MAX_PATH_COMPONENTS>;
/// cbindgen:ignore
type StandardValue<'a> = BaseValue<'a, Empty, PathComponents>;

/// cbindgen:ignore
#[derive(Debug)]
pub enum Value<'a> {
    Standard(StandardValue<'a>),
    PassportRequest(PassportRequest),
    PassportResponse(PassportResponse<'a>),
}

impl<'a> Value<'a> {
    pub fn encode<W: minicbor::encode::Write>(
        &self,
        w: W,
    ) -> Result<(), minicbor::encode::Error<W::Error>> {
        match self {
            Value::Standard(ref standard) => minicbor::encode(standard, w),
            Value::PassportRequest(ref passport_request) => {
                minicbor::encode(passport_request, w)
            }
            Value::PassportResponse(ref passport_response) => {
                minicbor::encode(passport_response, w)
            }
        }
    }

    pub fn ur_type(&self) -> &'static str {
        match self {
            Value::Standard(value) => value.ur_type(),
            Value::PassportRequest(_) => "crypto-request",
            Value::PassportResponse(_) => "crypto-response",
        }
    }
}

/// An uniform resource.
#[repr(C)]
pub enum UR_Value {
    /// `bytes`.
    Bytes { data: *const u8, len: usize },
    /// `crypto-hdkey`.
    CryptoHDKey(UR_HDKey),
    /// `crypto-psbt`.
    CryptoPSBT { data: *const u8, len: usize },
    /// Passport custom `crypto-request`.
    PassportRequest(UR_PassportRequest),
    /// Passport custom `crypto-response`.
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
        let value = match ur_type {
            "crypto-request" => Value::PassportRequest(
                minicbor::decode(message).map_err(|e| UR_Error::other(&e))?,
            ),
            _ => Value::Standard(
                StandardValue::from_ur(ur_type, message)
                    .map_err(|e| UR_Error::other(&e))?,
            ),
        };

        let value = match value {
            Value::Standard(StandardValue::Bytes(bytes)) => UR_Value::Bytes {
                data: bytes.as_ptr(),
                len: bytes.len(),
            },
            Value::Standard(StandardValue::CryptoPSBT(psbt)) => {
                UR_Value::CryptoPSBT {
                    data: psbt.as_ptr(),
                    len: psbt.len(),
                }
            }
            Value::PassportRequest(passport_request) => {
                UR_Value::PassportRequest(passport_request.into())
            }
            _ => {
                return Err(UR_Error::unsupported(
                    &"Unsupported uniform resource",
                ))
            }
        };

        Ok(value)
    }

    /// # Safety
    ///
    /// Same safety requirements as on [core::slice::from_raw_parts] when the
    /// value is:
    ///
    /// - `UR_Value::Bytes`.
    /// - `UR_Value::CryptoPSBT`.
    pub unsafe fn to_value(&self) -> Value<'_> {
        match self {
            UR_Value::Bytes { data, len } => {
                let buf = unsafe { slice::from_raw_parts(*data, *len) };
                Value::Standard(StandardValue::Bytes(buf.into()))
            }
            UR_Value::CryptoPSBT { data, len } => {
                let buf = unsafe { slice::from_raw_parts(*data, *len) };
                Value::Standard(StandardValue::CryptoPSBT(buf.into()))
            }
            UR_Value::CryptoHDKey(v) => {
                Value::Standard(StandardValue::CryptoHDKey(v.into()))
            }
            UR_Value::PassportRequest(_) => panic!(
                "Not implemented as it isn't needed. Should be unreachable"
            ),
            UR_Value::PassportResponse(v) => Value::PassportResponse(v.into()),
        }
    }
}

/// A `crypto-hdkey`.
#[repr(C)]
pub enum UR_HDKey {
    DerivedKey(UR_DerivedKey),
}

impl<'a, C> From<&'a UR_HDKey> for BaseHDKey<'a, C>
where
    C: ur::collections::Vec<PathComponent>,
{
    fn from(value: &'a UR_HDKey) -> BaseHDKey<'a, C> {
        match value {
            UR_HDKey::DerivedKey(v) => {
                BaseHDKey::DerivedKey(DerivedKey::from(v))
            }
        }
    }
}

/// Derived `crypto-hdkey`.
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
    pub use_info: UR_CryptoCoinInfo,
    /// Whether `use_info` is present.
    pub has_use_info: bool,
    /// How the key was derived.
    pub origin: UR_CryptoKeypath,
    /// Whether `origin` is present.
    pub has_origin: bool,
    /// The fingerprint of this key's direct ancestor.
    ///
    /// A value of `0` means that the fingerprint is not present.
    pub parent_fingerprint: u32,
}

impl<'a, C> From<&'a UR_DerivedKey> for DerivedKey<'a, C>
where
    C: ur::collections::Vec<PathComponent>,
{
    fn from(value: &'a UR_DerivedKey) -> DerivedKey<'a, C> {
        DerivedKey {
            is_private: value.is_private,
            key_data: value.key_data,
            chain_code: if value.has_chain_code {
                Some(value.chain_code)
            } else {
                None
            },
            use_info: if value.has_use_info {
                Some(CryptoCoinInfo::from(&value.use_info))
            } else {
                None
            },
            origin: if value.has_origin {
                Some(CryptoKeypath::from(&value.origin))
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
#[derive(Clone, Copy)]
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
#[derive(Clone)]
pub struct UR_CryptoCoinInfo {
    pub coin_type: UR_CoinType,
    pub network: u64,
}

impl From<&UR_CryptoCoinInfo> for CryptoCoinInfo {
    fn from(v: &UR_CryptoCoinInfo) -> CryptoCoinInfo {
        CryptoCoinInfo {
            coin_type: v.coin_type.into(),
            network: v.network,
        }
    }
}

/// Metadata for the complete or partial derivation path of a key.
#[repr(C)]
#[derive(Clone)]
pub struct UR_CryptoKeypath {
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
impl<C> From<CryptoKeypath<C>> for UR_CryptoKeypath
where
    C: ur::collections::Vec<PathComponent>,
{
    fn from(v: CryptoKeypath<C>) -> UR_CryptoKeypath {
        UR_CryptoKeypath {
            source_fingerprint: v
                .source_fingerprint
                .map(|v| v.get())
                .unwrap_or(0),
            depth: v.depth.unwrap_or(0),
            has_depth: v.depth.is_some(),
        }
    }
}

impl<C> From<&UR_CryptoKeypath> for CryptoKeypath<C>
where
    C: ur::collections::Vec<PathComponent>,
{
    fn from(v: &UR_CryptoKeypath) -> CryptoKeypath<C> {
        CryptoKeypath {
            components: C::default(),
            source_fingerprint: NonZeroU32::new(v.source_fingerprint),
            depth: if v.has_depth { Some(v.depth) } else { None },
        }
    }
}

/// Passport custom `crypto-request`.
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

/// Passport custom `crypto-request`.
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

/// Passport custom `crypto-response`.

/// Create a new `bytes` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_bytes(
    value: &mut UR_Value,
    data: *mut u8,
    len: usize,
) {
    *value = UR_Value::Bytes { data, len };
}

/// Create a new derived `crypto-hdkey` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_derived_key(
    value: &mut UR_Value,
    is_private: bool,
    key_data: &[u8; 33],
    chain_code: Option<&[u8; 32]>,
    use_info: Option<&UR_CryptoCoinInfo>,
    origin: Option<&UR_CryptoKeypath>,
    parent_fingerprint: u32,
) {
    *value = UR_Value::CryptoHDKey(UR_HDKey::DerivedKey(UR_DerivedKey {
        is_private,
        key_data: *key_data,
        chain_code: chain_code.copied().unwrap_or([0u8; 32]),
        has_chain_code: chain_code.is_some(),
        use_info: use_info.cloned().unwrap_or(UR_CryptoCoinInfo {
            coin_type: UR_CoinType::BTC,
            network: 0,
        }),
        has_use_info: use_info.is_some(),
        origin: origin.cloned().unwrap_or(UR_CryptoKeypath {
            source_fingerprint: 0,
            depth: 0,
            has_depth: false,
        }),
        has_origin: origin.is_some(),
        parent_fingerprint,
    }));
}

/// Create a new `crypto-psbt` UR.
#[no_mangle]
pub extern "C" fn ur_registry_new_crypto_psbt(
    value: &mut UR_Value,
    data: *mut u8,
    len: usize,
) {
    *value = UR_Value::CryptoPSBT { data, len };
}
/// Create a new Passport ustom `crypto-response` UR.
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
