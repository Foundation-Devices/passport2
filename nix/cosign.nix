# SPDX-FileCopyrightText: 2025 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  self,
  system,
  pkgs,
}: let
  src = pkgs.stdenv.mkDerivation {
    name = "cosign-src";
    src = self + "/ports/stm32/boards/Passport/tools/cosign";
    # TODO: account for darwin and arm architectures

    buildPhase = ''
      make
    '';

    installPhase = ''
      cp x86/release/cosign $out
    '';
    outputHash = "sha256-6GEfi9zx7+RLpIbxdT6K2uMRyJ1V78aVebM+vWZmwQY=";
    outputHashMode = "recursive";
  };
in {
  cosign = pkgs.stdenv.mkDerivation {
    pname = "cosign";
    inherit src;
  };
}
