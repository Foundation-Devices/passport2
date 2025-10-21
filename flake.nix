# SPDX-FileCopyrightText: 2025 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
{
  description = "Passport Core development environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    fenix = {
      url = "github:nix-community/fenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      fenix,
    }:
    let
      inherit (nixpkgs) lib;

      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "aarch64-linux"
        "x86_64-linux"
      ];

      forAllSystems = f: lib.genAttrs systems f;
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
          ci-pkgs = with pkgs; {
            inherit just reuse python313Packages.pycodestyle;
          };
        in
        ci-pkgs
        // import ./nix/rust-toolchain.nix {
          inherit
            self
            system
            pkgs
            fenix
            ;
        }
        // import ./nix/cosign.nix { inherit self system pkgs; }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config = {
              allowUnfree = true;
            };
          };
          customPackages = self.packages.${system};

          buildPackages =
            with pkgs;
            [
              # cmake
              curl
              gcc-arm-embedded
              git
              gnumake
              just
              openssl
              pkg-config
              reuse
              autoconf
              automake
              pkg-config
              cbindgen
              # unixtools.xxd
            ]
            ++ (with customPackages; [
              cosign
            ]);

          devPackages =
            buildPackages
            ++ (with pkgs; [
              minicom
              sdl2
              openocd
            ]);


        in
        {
          # full development shell
          default = mkShell devPackages;
          # minimal build shell
          build = mkShell buildPackages;
        }
      );
    };
}
