// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

pub mod io {
    pub mod spi_nor;
}

pub mod rand {
    pub fn passport_rng() -> rand::rngs::ThreadRng {
        rand::thread_rng()
    }
}

pub mod secp256k1 {
    pub use secp256k1::SECP256K1;
}
