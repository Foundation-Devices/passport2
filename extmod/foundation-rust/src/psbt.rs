// SPDX-FileCopyrightText: 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use core::{
    ffi::{c_char, c_void},
    ptr::addr_of,
};
use embedded_storage_nom::{rc::Rc, Bytes};
use foundation_psbt::validation::{Error, ValidationError};
use once_cell::unsync::Lazy;

use crate::{bip32::Xpriv, flash::STORAGE, secp256k1::PRE_ALLOCATED_CTX};

/// cbindgen:ignore
const INTERNAL_BUFFER_LEN: usize = 32;
/// cbindgen:ignore
const MAX_PUBKEYS: usize = 15;

/// The Bitcoin network.
///
/// cbindgen:rename-all=ScreamingSnakeCase
/// cbindgen:prefix-with-name
#[repr(C)]
pub enum Network {
    Mainnet,
    Testnet,
}

impl From<Network> for foundation_psbt::address::Network {
    fn from(n: Network) -> Self {
        match n {
            Network::Mainnet => foundation_psbt::address::Network::Mainnet,
            Network::Testnet => foundation_psbt::address::Network::Testnet,
        }
    }
}

/// The result of the PSBT validation.
/// cbindgen:rename-all=ScreamingSnakeCase
/// cbindgen:prefix-with-name
#[derive(Debug)]
#[repr(C)]
pub enum ValidationResult {
    /// Validation succeeded.
    Ok {
        total_with_change: u64,
        total_change: u64,
        fee: u64,
        is_self_send: bool,
    },
    /// Internal error of the validation function.
    InternalError,
    /// The extended private key passed is invalid.
    InvalidXpriv,
    /// Failed to parse the PSBT.
    ParserError,
    InvalidWitnessScript,
    InvalidRedeemScript,
    UnsupportedSighash,
    TxidMismatch,
    MissingOutputPoint {
        index: u64,
    },
    MissingPreviousTxid,
    MissingRedeemWitnessScript {
        index: u64,
    },
    TaprootOutputInvalidPublicKey {
        index: u64,
    },
    TooManyInputs,
    TooManyOutputs,
    TooManyOutputKeys {
        index: u64,
    },
    MultipleKeysNotExpected {
        index: u64,
    },
    FraudulentOutputPublicKey {
        index: u64,
    },
    MissingOutput {
        index: u64,
    },
    UnknownOutputScript {
        index: u64,
    },
    FraudulentWitnessUtxo {
        index: u64,
    },
}

impl From<ValidationError> for ValidationResult {
    fn from(e: ValidationError) -> Self {
        match e {
            ValidationError::InternalError => Self::InternalError,
            ValidationError::InvalidWitnessScript => Self::InvalidWitnessScript,
            ValidationError::InvalidRedeemScript => Self::InvalidRedeemScript,
            ValidationError::UnsupportedSighash => Self::UnsupportedSighash,
            ValidationError::TxidMismatch => Self::TxidMismatch,
            ValidationError::MissingOutputPoint { index } => {
                Self::MissingOutputPoint { index }
            }
            ValidationError::MissingPreviousTxid => Self::MissingPreviousTxid,
            ValidationError::MissingRedeemWitnessScript { index } => {
                Self::MissingRedeemWitnessScript { index }
            }
            ValidationError::TaprootOutputInvalidPublicKey { index } => {
                Self::TaprootOutputInvalidPublicKey { index }
            }
            ValidationError::TooManyInputs => Self::TooManyInputs,
            ValidationError::TooManyOutputs => Self::TooManyOutputs,
            ValidationError::TooManyOutputKeys { index } => {
                Self::TooManyOutputKeys { index }
            }
            ValidationError::MultipleKeysNotExpected { index } => {
                Self::MultipleKeysNotExpected { index }
            }
            ValidationError::FraudulentOutputPublicKey { index } => {
                Self::FraudulentOutputPublicKey { index }
            }
            ValidationError::MissingOutput { index } => {
                Self::MissingOutput { index }
            }
            ValidationError::UnknownOutputScript { index } => {
                Self::UnknownOutputScript { index }
            }
            ValidationError::FraudulentWitnessUtxo { index } => {
                Self::FraudulentWitnessUtxo { index }
            }
        }
    }
}

/// Events that happen during PSBT validation.
/// cbindgen:rename-all=ScreamingSnakeCase
/// cbindgen:prefix-with-name
#[repr(C)]
pub enum ValidationEvent {
    Progress(u64),
    OutputAddress { amount: u64, address: [c_char; 91] },
    ChangeAddress { amount: u64, address: [c_char; 91] },
}

fn to_static_cstr<const N: usize>(s: &[u8], result: &mut [c_char; N]) {
    result.fill(0);

    let len = s.len().min(N - 1);
    for i in 0..len {
        result[i] = s[i] as c_char;
    }
}

impl From<foundation_psbt::validation::Event> for ValidationEvent {
    fn from(e: foundation_psbt::validation::Event) -> Self {
        use foundation_psbt::validation::Event;

        match e {
            Event::Progress(v) => ValidationEvent::Progress(v),
            Event::OutputAddress { amount, address } => {
                let mut address_cstr = [0; 91];
                to_static_cstr(address.as_bytes(), &mut address_cstr);

                ValidationEvent::OutputAddress {
                    amount: amount.to_sat(),
                    address: address_cstr,
                }
            }
            Event::ChangeAddress { amount, address } => {
                let mut address_cstr = [0; 91];
                to_static_cstr(address.as_bytes(), &mut address_cstr);

                ValidationEvent::ChangeAddress {
                    amount: amount.to_sat(),
                    address: address_cstr,
                }
            }
        }
    }
}

pub type ValidationEventCallback =
    extern "C" fn(*mut c_void, &ValidationEvent) -> bool;

/// Validate a PSBT in the SPI flash at `offset` of length `len`, in bytes.
#[export_name = "foundation_psbt_validate"]
pub extern "C" fn validate(
    offset: usize,
    len: usize,
    network: Network,
    xpriv: &Xpriv,
    data: *mut c_void,
    handle_event: ValidationEventCallback,
    result: &mut ValidationResult,
) -> bool {
    let storage = Lazy::force(unsafe { &*addr_of!(STORAGE) });
    let psbt = match Bytes::<_, INTERNAL_BUFFER_LEN>::new(
        offset,
        len,
        Rc::clone(storage),
    ) {
        Ok(v) => v,
        // This error should be unreachable as it can only happen if the
        // storage device is already borrowed.
        Err(_) => {
            *result = ValidationResult::InternalError;
            return false;
        }
    };

    let xpriv = match foundation_bip32::Xpriv::try_from(xpriv) {
        Ok(v) => v,
        // This should be unreachable, as the MicroPython code should make
        // sure that we have a valid private key.
        Err(_) => {
            *result = ValidationResult::InvalidXpriv;
            return false;
        }
    };

    match foundation_psbt::validation::validate::<
        _,
        _,
        _,
        nom::error::Error<_>,
        MAX_PUBKEYS,
    >(network.into(), psbt, &PRE_ALLOCATED_CTX, xpriv, |e| {
        if handle_event(data, &ValidationEvent::from(e)) {
            #[cfg(target_arch = "arm")]
            unsafe {
                lv_refresh();
            }
        }
    }) {
        Ok(details) => {
            *result = ValidationResult::Ok {
                total_with_change: details.total_with_change.to_sat(),
                total_change: details.total_change.to_sat(),
                fee: details.fee().to_sat(),
                is_self_send: details.is_self_send(),
            };

            true
        }
        Err(Error::Parse(e)) => {
            log::error!("parser error: {e:?}");
            *result = ValidationResult::ParserError;
            false
        }
        Err(Error::Validation(e)) => {
            *result = ValidationResult::from(e);
            false
        }
        Err(Error::AddressRender(e)) => {
            log::error!("parser error: {e:?}");
            *result = ValidationResult::ParserError;
            false
        }
    }
}

extern "C" {
    // This is defined on ports/stm32/boards/Passport/common/utils.c.
    //
    // We need to allow LVGL to refresh the display after each event, at least
    // for the progress update, as the MicroPython code won't be able to do it.
    #[cfg(target_arch = "arm")]
    fn lv_refresh();
}
