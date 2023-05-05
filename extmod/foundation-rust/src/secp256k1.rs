// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use once_cell::sync::Lazy;
use secp256k1::{
    ffi::types::AlignedType, AllPreallocated, KeyPair, Message, Secp256k1,
};

/// cbindgen:ignore
static mut PRE_ALLOCATED_CTX_BUF: [AlignedType; 20] = [AlignedType::ZERO; 20];

/// cbindgen:ignore
static PRE_ALLOCATED_CTX: Lazy<Secp256k1<AllPreallocated<'static>>> =
    Lazy::new(|| {
        let buf = unsafe { &mut PRE_ALLOCATED_CTX_BUF };
        Secp256k1::preallocated_new(buf)
            .expect("the pre-allocated context buf should have enough space")
    });

/// Computes a Schnorr signature over the message `data`.
///
/// - `data` is the message hash.
/// - `secret_key` is the secret key used to sign the message.
/// - `signature` is the output of the resulting signature.
#[export_name = "foundation_secp256k1_schnorr_sign"]
pub extern "C" fn secp256k1_sign_schnorr(
    data: &[u8; 32],
    secret_key: &[u8; 32],
    signature: &mut [u8; 64],
) {
    let keypair = KeyPair::from_seckey_slice(&PRE_ALLOCATED_CTX, secret_key)
        .expect("invalid secret key");

    let msg = Message::from_slice(data).unwrap();
    let sig =
        PRE_ALLOCATED_CTX.sign_schnorr_with_rng(&msg, &keypair, &mut rng());
    signature.copy_from_slice(sig.as_ref());
}

#[cfg(all(target_os = "none", target_arch = "arm"))]
fn rng() -> crate::rand::PassportRng {
    crate::rand::PassportRng
}

#[cfg(not(all(target_os = "none", target_arch = "arm")))]
fn rng() -> rand::rngs::OsRng {
    rand::rngs::OsRng
}
