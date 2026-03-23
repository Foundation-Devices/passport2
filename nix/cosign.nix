# SPDX-FileCopyrightText: 2025 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  self,
  pkgs,
  ...
}: {
  cosign = pkgs.stdenv.mkDerivation {
    pname = "passport-cosign";
    version = "0.1.0";
    src = self + "/ports/stm32/boards/Passport";
    nativeBuildInputs = [ pkgs.pkg-config ];
    buildInputs = [ pkgs.openssl ];
    dontConfigure = true;
    NIX_CFLAGS_COMPILE = "-Wno-error=int-conversion";

    buildPhase = ''
      runHook preBuild
      make -C tools/cosign
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out/bin
      cp tools/cosign/x86/release/cosign $out/bin/cosign
      runHook postInstall
    '';
  };
}
