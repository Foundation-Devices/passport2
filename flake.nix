# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
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
          ciPkgs = {
            inherit (pkgs)
              just
              reuse
              ;
            pycodestyle = pkgs.python313Packages.pycodestyle;
          };
        in
        ciPkgs
        // import ./nix/rust-toolchain.nix {
          inherit
            self
            system
            pkgs
            fenix
            ;
        }
        // import ./nix/mpy-cross.nix { inherit self pkgs; }
        // import ./nix/cosign.nix { inherit self pkgs; }
        // import ./nix/add-secrets.nix { inherit self pkgs; }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          customPackages = self.packages.${system};
          # nixpkgs still ships Pillow 12.3.0, which is affected by open Pillow
          # advisories fixed in 13.0.0. Override it for the whole Python package
          # set, so packages that depend on Pillow (imageio) use the same copy as
          # the shell. Remove once nixpkgs carries Pillow >= 13.0.0.
          python3 = pkgs.python3.override {
            self = python3;
            packageOverrides = pyFinal: pyPrev: {
              pillow = pyPrev.pillow.overridePythonAttrs (old: rec {
                version = "13.0.0";
                src = pkgs.fetchPypi {
                  pname = "pillow";
                  inherit version;
                  hash = "sha256-zc0bolgXj3NW10FwyagbpOq2pdVXSLxAKloqb+a+NRA=";
                };
                # The shell needs the library, not its test suite, and nixpkgs'
                # list of disabled tests is tuned for 12.3.0.
                doCheck = false;
              });
              # imageio needs only numpy and Pillow at runtime. Its tests pull in
              # every optional codec (pillow-heif, astropy, av, ...), which would
              # all rebuild against the overridden Pillow, and one pillow-heif
              # pixel comparison is off by one against 13.0.0.
              imageio = pyPrev.imageio.overridePythonAttrs { doCheck = false; };
            };
          };
          python3Packages = python3.pkgs;
          embit = python3Packages.buildPythonPackage rec {
            pname = "embit";
            version = "0.8.0";
            pyproject = true;
            src = pkgs.fetchPypi {
              inherit pname version;
              hash = "sha256-i/SxAHPGdAA3DOUj+xbwNf51n2/dmHxXm9zCaNde13A=";
            };
            build-system = with python3Packages; [ setuptools wheel ];
            pythonImportsCheck = [ "embit.descriptor.arguments" ];
          };
          runtimeLibPath = with pkgs; pkgs.lib.makeLibraryPath [
            stdenv.cc.cc.lib
            glib
            wayland
            libdecor
            libglvnd
            libICE
            libSM
            libx11
            libxau
            libxcb
            libxdmcp
            libxext
            libxkbcommon
            SDL2
            sdl3
            zlib
          ];
          mkShell = packages:
            pkgs.mkShellNoCC (
              {
                inherit packages;
                hardeningDisable = [ "all" ];
                CC = "${pkgs.gcc13}/bin/gcc";
                CXX = "${pkgs.gcc13}/bin/g++";
                LD_LIBRARY_PATH = runtimeLibPath;
                MPY_CROSS = "${customPackages.mpy-cross}/bin/mpy-cross";
                shellHook = ''
                  if [ -n "''${WAYLAND_DISPLAY:-}" ] && [ -z "''${SDL_VIDEODRIVER:-}" ]; then
                    export SDL_VIDEODRIVER=wayland
                  fi
                  if [ -n "''${WAYLAND_DISPLAY:-}" ] && [ -z "''${SDL_VIDEO_WAYLAND_PREFER_LIBDECOR:-}" ]; then
                    export SDL_VIDEO_WAYLAND_PREFER_LIBDECOR=1
                  fi
                '';
              }
              // lib.optionalAttrs pkgs.stdenv.hostPlatform.isLinux {
                QT_QPA_PLATFORM = "xcb";
                SDL_RENDER_DRIVER = "software";
              }
            );

          buildPackages =
            with pkgs;
            [
              autoconf
              automake
              curl
              gcc13
              gcc-arm-embedded-13
              git
              gnumake
              just
              libffi
              libtool
              libusb1
              openssl
              pkg-config
              python3
              python3Packages.autopep8
              python3Packages.imageio
              (python3Packages.opencv4.override {
                enableGtk3 = stdenv.hostPlatform.isLinux;
              })
              python3Packages.pip
              python3Packages.pillow
              python3Packages.pytest
              python3Packages.pysdl2
              python3Packages.virtualenv
              SDL2
              reuse
              rust-cbindgen
              xterm
            ]
            ++ [
              embit
              customPackages.add-secrets
              customPackages.cosign
              customPackages.mpy-cross
              customPackages.rust-core
            ];

          devPackages =
            buildPackages
            ++ (with pkgs; [
              fontmiscmisc
              minicom
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
