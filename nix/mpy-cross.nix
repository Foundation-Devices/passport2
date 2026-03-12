# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  self,
  pkgs,
  ...
}:
let
  foundationRust = pkgs.rustPlatform.buildRustPackage rec {
    pname = "passport-foundation-rust";
    version = "0.1.0";
    src = self + "/extmod/foundation-rust";
    cargoLock = {
      lockFile = src + "/Cargo.lock";
    };
    doCheck = false;
    buildFeatures = [ "std" ];
    installPhase = ''
      runHook preInstall
      mkdir -p $out/include $out/lib
      cp include/foundation.h $out/include/foundation.h
      libfoundation=$(find target -type f -path "*/release/libfoundation.a" | head -n1)
      cp "$libfoundation" $out/lib/libfoundation.a
      runHook postInstall
    '';
  };
in
{
  foundation-rust = foundationRust;
  mpy-cross = pkgs.gcc13Stdenv.mkDerivation {
    pname = "passport-mpy-cross";
    version = "0.1.0";
    src = self;
    nativeBuildInputs = with pkgs; [
      gnumake
      python3
    ];
    dontConfigure = true;
    buildPhase = ''
      runHook preBuild
      make -C mpy-cross FOUNDATION_RUST=${foundationRust} FOUNDATION_RUST_LIB=${foundationRust}/lib/libfoundation.a FOUNDATION_RUST_SRC=
      runHook postBuild
    '';
    installPhase = ''
      runHook preInstall
      mkdir -p $out/bin
      cp mpy-cross/mpy-cross $out/bin/mpy-cross
      runHook postInstall
    '';
  };
}
