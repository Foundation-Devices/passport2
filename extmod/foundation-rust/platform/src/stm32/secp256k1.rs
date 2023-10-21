// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

//! Pre-allocated secp256k1 context.

use core::ops::Deref;

use once_cell::sync::Lazy;
use secp256k1::{ffi::types::AlignedType, AllPreallocated, Secp256k1};

use crate::rand;

/// A global [`secp256k1`] context.
#[derive(Debug)]
pub struct GlobalContext {
    __private: (),
}

impl Deref for GlobalContext {
    type Target = Secp256k1<AllPreallocated<'static>>;

    fn deref(&self) -> &Self::Target {
        static mut CONTEXT_BUF: [AlignedType; 20] = [AlignedType::ZERO; 20];

        static CONTEXT: Lazy<Secp256k1<AllPreallocated<'static>>> =
            Lazy::new(|| {
                // SAFETY: This assumes that this initialization only happens
                // _once_ and that secp256k1 _does not mutate_ the context when
                // doing any operation as this context is only for storing data
                // that is costly to compute each time, so essentially a cache.
                let buf = unsafe { &mut CONTEXT_BUF };
                let mut ctx = Secp256k1::preallocated_new(buf).expect(
                    "the pre-allocated context buf should have enough space",
                );
                ctx.randomize(&mut rand::passport_rng());
                ctx
            });

        &CONTEXT
    }
}

/// Global pre-allocated context for [`secp256k1`] with all features.
pub static SECP256K1: &GlobalContext = &GlobalContext { __private: () };
