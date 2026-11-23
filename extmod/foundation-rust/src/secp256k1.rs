// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

use bitcoin_hashes::{sha256, HashEngine};
use core::ptr;
use once_cell::sync::Lazy;
use secp256k1::{
    ffi::types::AlignedType, AllPreallocated, Keypair, Message, Scalar,
    Secp256k1, SecretKey,
};

/// cbindgen:ignore
static mut PRE_ALLOCATED_CTX_BUF: [AlignedType; 20] = [AlignedType::ZERO; 20];

/// cbindgen:ignore
pub static PRE_ALLOCATED_CTX: Lazy<Secp256k1<AllPreallocated<'static>>> =
    Lazy::new(|| {
        // SAFETY:
        //
        // This pre-allocated buffer safety depends on trusting libsecp256k1
        // that it writes the context buffer only once for initialization and
        // then only performs reads to it.
        let buf = unsafe { &mut *ptr::addr_of_mut!(PRE_ALLOCATED_CTX_BUF) };

        Secp256k1::preallocated_new(buf)
            .expect("the pre-allocated context buf should have enough space")
    });

/// Calculate a "Schnorr" public key from the secret key.
///
/// See also:
///
/// - https://github.com/bitcoin/bips/blob/master/bip-0340.mediawiki#user-content-Public_Key_Conversion
#[export_name = "foundation_secp256k1_public_key_schnorr"]
pub extern "C" fn secp256k1_public_key_schnorr(
    secret_key: &[u8; 32],
    public_key: &mut [u8; 32],
) {
    let keypair = Keypair::from_seckey_slice(&PRE_ALLOCATED_CTX, secret_key)
        .expect("invalid secret key");
    let compressed_key = keypair.public_key().serialize();
    public_key.copy_from_slice(&compressed_key[1..]);
}

/// Computes a ECDSA signature over the message `data`.
///
/// - `data` is the message hash.
/// - `secret_key` is the secret key used to sign the message.
/// - `signature` is the output of the resulting signature.
#[export_name = "foundation_secp256k1_sign_ecdsa"]
pub extern "C" fn secp256k1_sign_ecdsa(
    data: &[u8; 32],
    secret_key: &[u8; 32],
    signature: &mut [u8; 64],
) {
    let secret_key =
        SecretKey::from_slice(secret_key).expect("invalid secret key");

    let msg = Message::from_digest_slice(data).unwrap();
    let sig = PRE_ALLOCATED_CTX.sign_ecdsa(&msg, &secret_key);
    signature.copy_from_slice(&sig.serialize_compact());
}

/// Computes a Schnorr signature over the message `data`.
///
/// - `data` is the message hash.
/// - `secret_key` is the secret key used to sign the message.
/// - `signature` is the output of the resulting signature.
#[export_name = "foundation_secp256k1_sign_schnorr"]
pub extern "C" fn secp256k1_sign_schnorr(
    data: &[u8; 32],
    secret_key: &[u8; 32],
    signature: &mut [u8; 64],
) {
    let keypair = Keypair::from_seckey_slice(&PRE_ALLOCATED_CTX, secret_key)
        .expect("invalid secret key");

    let sig =
        PRE_ALLOCATED_CTX.sign_schnorr_with_rng(data, &keypair, &mut rng());
    signature.copy_from_slice(sig.as_ref());
}

/// Computes a BIP-341 Taproot key path signature over the message `data`.
///
/// - `data` is the message hash.
/// - `secret_key` is the internal secret key, before the Taproot tweak.
/// - `merkle_root` is the Merkle root of the script tree, or null when the
///   output key commits to no script tree.
/// - `signature` is the output of the resulting signature.
///
/// See also:
///
/// - https://github.com/bitcoin/bips/blob/master/bip-0341.mediawiki#constructing-and-spending-taproot-outputs
#[export_name = "foundation_secp256k1_sign_schnorr_taproot"]
pub extern "C" fn secp256k1_sign_schnorr_taproot(
    data: &[u8; 32],
    secret_key: &[u8; 32],
    merkle_root: Option<&[u8; 32]>,
    signature: &mut [u8; 64],
) {
    let mut keypair = taproot_tweak(secret_key, merkle_root);

    let sig =
        PRE_ALLOCATED_CTX.sign_schnorr_with_rng(data, &keypair, &mut rng());
    keypair.non_secure_erase();
    signature.copy_from_slice(sig.as_ref());
}

/// Applies the BIP-341 `TapTweak` to `secret_key`, negating it first when its
/// public key has an odd Y coordinate.
fn taproot_tweak(
    secret_key: &[u8; 32],
    merkle_root: Option<&[u8; 32]>,
) -> Keypair {
    let keypair = Keypair::from_seckey_slice(&PRE_ALLOCATED_CTX, secret_key)
        .expect("invalid secret key");
    let (internal_key, _) = keypair.x_only_public_key();

    let tag = sha256::Hash::hash(b"TapTweak");
    let mut engine = sha256::Hash::engine();
    engine.input(tag.as_ref());
    engine.input(tag.as_ref());
    engine.input(&internal_key.serialize());
    if let Some(merkle_root) = merkle_root {
        engine.input(merkle_root);
    }
    let tweak = sha256::Hash::from_engine(engine).to_byte_array();

    let tweak = Scalar::from_be_bytes(tweak).expect("tweak is out of range");
    keypair
        .add_xonly_tweak(&PRE_ALLOCATED_CTX, &tweak)
        .expect("tweak produced an invalid key")
}

#[cfg(target_arch = "arm")]
fn rng() -> crate::rand::PassportRng {
    crate::rand::PassportRng
}

#[cfg(not(target_arch = "arm"))]
fn rng() -> rand::rngs::ThreadRng {
    rand::thread_rng()
}

#[cfg(test)]
mod tests {
    use super::*;
    use secp256k1::schnorr::Signature;

    /// BIP-341 wallet test vectors, `keyPathSpending`: internal secret key,
    /// Merkle root, and the expected tweaked secret key.
    const KEY_PATH_VECTORS: &[(&str, Option<&str>, &str)] = &[
        (
            "6b973d88838f27366ed61c9ad6367663045cb456e28335c109e30717ae0c6baa",
            None,
            "2405b971772ad26915c8dcdf10f238753a9b837e5f8e6a86fd7c0cce5b7296d9",
        ),
        (
            "1e4da49f6aaf4e5cd175fe08a32bb5cb4863d963921255f33d3bc31e1343907f",
            Some("5b75adecf53548f3ec6ad7d78383bf84cc57b55a3127c72b9a2481752dd88b21"),
            "ea260c3b10e60f6de018455cd0278f2f5b7e454be1999572789e6a9565d26080",
        ),
        (
            "d3c7af07da2d54f7a7735d3d0fc4f0a73164db638b2f2f7c43f711f6d4aa7e64",
            Some("c525714a7f49c28aedbbba78c005931a81c234b2f6c99a73e4d06082adc8bf2b"),
            "97323385e57015b75b0339a549c56a948eb961555973f0951f555ae6039ef00d",
        ),
        (
            "f36bb07a11e469ce941d16b63b11b9b9120a84d9d87cff2c84a8d4affb438f4e",
            Some("ccbd66c6f7e8fdab47b3a486f59d28262be857f30d4773f2d5ea47f7761ce0e2"),
            "a8e7aa924f0d58854185a490e6c41f6efb7b675c0f3331b7f14b549400b4d501",
        ),
        (
            "415cfe9c15d9cea27d8104d5517c06e9de48e2f986b695e4f5ffebf230e725d8",
            Some("2f6b2c5397b6d68ca18e09a3f05161668ffe93a988582d55c6f07bd5b3329def"),
            "241c14f2639d0d7139282aa6abde28dd8a067baa9d633e4e7230287ec2d02901",
        ),
        (
            "c7b0e81f0a9a0b0499e112279d718cca98e79a12e2f137c72ae5b213aad0d103",
            Some("6c2dc106ab816b73f9d07e3cd1ef2c8c1256f519748e0813e4edd2405d277bef"),
            "65b6000cd2bfa6b7cf736767a8955760e62b6649058cbc970b7c0871d786346b",
        ),
        (
            "77863416be0d0665e517e1c375fd6f75839544eca553675ef7fdf4949518ebaa",
            Some("ab179431c28d3b68fb798957faf5497d69c883c6fb1e1cd9f81483d87bac90cc"),
            "ec18ce6af99f43815db543f47b8af5ff5df3b2cb7315c955aa4a86e8143d2bf5",
        ),
    ];

    fn hex32(text: &str) -> [u8; 32] {
        let mut bytes = [0; 32];
        for (byte, pair) in bytes.iter_mut().zip(text.as_bytes().chunks(2)) {
            let pair = core::str::from_utf8(pair).unwrap();
            *byte = u8::from_str_radix(pair, 16).unwrap();
        }
        bytes
    }

    #[test]
    fn taproot_tweak_matches_bip341_vectors() {
        for (internal, merkle_root, tweaked) in KEY_PATH_VECTORS {
            let merkle_root = merkle_root.map(hex32);
            let keypair = taproot_tweak(&hex32(internal), merkle_root.as_ref());
            assert_eq!(keypair.secret_bytes(), hex32(tweaked));
        }
    }

    #[test]
    fn taproot_signature_verifies_against_the_output_key() {
        let data = [0x42; 32];
        for (internal, merkle_root, tweaked) in KEY_PATH_VECTORS {
            let merkle_root = merkle_root.map(hex32);
            let mut signature = [0; 64];
            secp256k1_sign_schnorr_taproot(
                &data,
                &hex32(internal),
                merkle_root.as_ref(),
                &mut signature,
            );

            let output_key =
                Keypair::from_seckey_slice(&PRE_ALLOCATED_CTX, &hex32(tweaked))
                    .unwrap()
                    .x_only_public_key()
                    .0;
            let signature = Signature::from_slice(&signature).unwrap();
            PRE_ALLOCATED_CTX
                .verify_schnorr(&signature, &data, &output_key)
                .unwrap();
        }
    }
}
