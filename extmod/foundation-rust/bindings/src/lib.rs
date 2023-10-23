// SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#![cfg_attr(all(target_arch = "arm", target_os = "none"), no_std)]
#![allow(non_camel_case_types)]

pub mod io;
pub mod secp256k1;
pub mod ur;
