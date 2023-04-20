use bitcoin::key::{KeyPair, Secp256k1};
use bitcoin::secp256k1::{All, Message};

pub struct secp256k1_t(Secp256k1<All>);

pub struct secp256k1_keypair_t(KeyPair);

#[no_mangle]
pub extern "C" fn foundation_secp256k1_sign_schnorr(secp: &secp256k1_t, keypair: &secp256k1_keypair_t) {
    secp.0.sign_schnorr_with_aux_rand(&Message::from_slice(&[0]).unwrap(), &keypair.0, &[0; 32]);
}
