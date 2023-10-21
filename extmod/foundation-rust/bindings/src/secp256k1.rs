// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

use passport_platform::{rand, secp256k1::SECP256K1};
use secp256k1::{Keypair, Message};

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
    let keypair = Keypair::from_seckey_slice(&SECP256K1, secret_key)
        .expect("invalid secret key");

    let msg = Message::from_digest_slice(data).unwrap();
    let sig = SECP256K1.sign_schnorr_with_rng(
        &msg,
        &keypair,
        &mut rand::passport_rng(),
    );
    signature.copy_from_slice(sig.as_ref());
}
