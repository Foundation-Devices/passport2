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
        // import ./nix/cosign.nix { inherit self system pkgs; }
      );

      devShells = forAllSystems (
        system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
          };
          customPackages = self.packages.${system};
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
            pkgs.mkShellNoCC {
              inherit packages;
              hardeningDisable = [ "all" ];
              CC = "${pkgs.gcc13}/bin/gcc";
              CXX = "${pkgs.gcc13}/bin/g++";
              MPY_CROSS = "${customPackages.mpy-cross}/bin/mpy-cross";
              shellHook = ''
                if [ -n "''${LD_LIBRARY_PATH:-}" ]; then
                  export LD_LIBRARY_PATH=''${LD_LIBRARY_PATH}:${runtimeLibPath}
                else
                  export LD_LIBRARY_PATH=${runtimeLibPath}
                fi
                if [ -n "''${WAYLAND_DISPLAY:-}" ] && [ -z "''${SDL_VIDEODRIVER:-}" ]; then
                  export SDL_VIDEODRIVER=wayland
                fi
                if [ -n "''${WAYLAND_DISPLAY:-}" ] && [ -z "''${SDL_VIDEO_WAYLAND_PREFER_LIBDECOR:-}" ]; then
                  export SDL_VIDEO_WAYLAND_PREFER_LIBDECOR=1
                fi
                if [ -z "''${SDL_RENDER_DRIVER:-}" ]; then
                  export SDL_RENDER_DRIVER=software
                fi
                if [ "$(uname -s)" = "Linux" ] && [ -z "''${QT_QPA_PLATFORM:-}" ]; then
                  export QT_QPA_PLATFORM=xcb
                fi
              '';
            };

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
              python3Packages.pip
              python3Packages.virtualenv
              reuse
              rust-cbindgen
              xterm
            ]
            ++ [
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
              SDL2
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
