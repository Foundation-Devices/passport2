# SPDX-FileCopyrightText: 2025 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  self,
  pkgs,
  ...
}: {
  add-secrets = pkgs.stdenv.mkDerivation {
    pname = "passport-add-secrets";
    version = "0.1.0";
    src = self + "/ports/stm32/boards/Passport";
    dontConfigure = true;
    NIX_CFLAGS_COMPILE = "-Wno-error=int-conversion";

    buildPhase = ''
      runHook preBuild
      make -C tools/add-secrets
      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mkdir -p $out/bin
      cp tools/add-secrets/x86/release/add-secrets $out/bin/add-secrets
      runHook postInstall
    '';
  };
}
