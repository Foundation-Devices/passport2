// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

/// Enables STM32-specific code.
macro_rules! cfg_stm32 {
    ($($item:item)*) => {
        $(
            #[cfg(all(target_arch = "arm", target_os = "none"))]
            $item
        )*
    }
}

/// Enables unix-specific code.
macro_rules! cfg_unix {
    ($($item:item)*) => {
        $(
            #[cfg(target_family = "unix")]
            $item
        )*
    }
}

cfg_stm32! {
    pub use passport_platform_stm32::rand;
    pub use passport_platform_stm32::secp256k1;
}

cfg_unix! {
    pub use passport_platform_unix::rand;
    pub use passport_platform_unix::secp256k1;
}
