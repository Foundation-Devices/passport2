# SPDX-FileCopyrightText: 2025 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  self,
  system,
  pkgs,
  fenix,
}: let
  toolchainSha256 = "sha256-3St/9/UKo/6lz2Kfq2VmlzHyufduALpiIKaaKX4Pq0g=";

  baseToolchain = fenix.packages.${system}.fromToolchainFile {
    file = self + "/extmod/foundation-rust/rust-toolchain.toml";
    sha256 = toolchainSha256;
  };

  thumbv7emHf = fenix.packages.${system}.targets.thumbv7em-none-eabihf.fromToolchainFile {
    file = self + "/extmod/foundation-rust/rust-toolchain.toml";
    sha256 = toolchainSha256;
  };
in {
  rust-core = fenix.packages.${system}.combine [
    baseToolchain
    thumbv7emHf
  ];
  rust-analyzer = fenix.packages.${system}.rust-analyzer;
}
