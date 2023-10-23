# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Justfile - Root-level Justfile for Passport

export DOCKER_IMAGE := env_var_or_default("DOCKER_IMAGE", "foundation-devices/passport2:latest")

set dotenv-load

# Build the docker image
build-docker:
    docker build -t ${DOCKER_IMAGE} .

# Build the firmware.
build-firmware screen="mono":
    ./run.sh just ports/stm32/build {{screen}}

# build the bootloader inside docker
build-bootloader screen="mono":
    ./run.sh just ports/stm32/boards/Passport/bootloader/build {{screen}}

# Run the built firmware through SHA256
verify-sha sha screen="mono":
   #!/usr/bin/env bash

   sha=$(shasum -a 256 ports/stm32/build-Passport/firmware-{{uppercase(screen)}}.bin | awk '{print $1}')

   if [ -z "${sha}" ]; then
       exit 1
   fi

   echo -e "Expected SHA:\t{{sha}}"
   echo -e "Actual SHA:\t${sha}"
   if [ "$sha" = "{{sha}}" ]; then
       echo "Hashes match!"
   else
       echo "ERROR: Hashes DO NOT match!"
       exit 1
   fi

# Build tools.
tools: build-add-secrets build-cosign

# Build the add-secrets tool.
build-add-secrets:
    ./run.sh make -C ports/stm32/boards/Passport/tools/add-secrets

# Build the cosign tool.
build-cosign:
    ./run.sh make -C ports/stm32/boards/Passport/tools/cosign

# Sign the built firmware using a private key and the cosign tool
sign keypath version screen="mono": (build-firmware screen) (build-cosign)
    ./run.sh just cosign_filepath=build-Passport/firmware-{{uppercase(screen)}}.bin \
                  cosign_keypath={{keypath}} \
                  {{version}} \
                  {{screen}} \
                  ports/stm32/sign

# Clean firmware build
clean:
    ./run.sh just ports/stm32/clean

# Clean bootloader build
clean-bootloader:
    ./run.sh just ports/stm32/boards/Passport/bootloader/clean

# Clean simulator build
clean-simulator $USE_DOCKER="false":
    just simulator/clean

# Build simulator
build-simulator screen="mono" $USE_DOCKER="false":
    just simulator/build {{screen}}

# Run the simulator.
sim screen="mono" ext="" $USE_DOCKER="false":
    just simulator/sim {{screen}} {{ext}}

# Run unit tests.
test:
  just simulator/build color
  cd ports/stm32/boards/Passport/modules/tests; python3 -m pytest . --simulatordir=$(pwd)/simulator

# Lint the codebase.
lint:
    ./run.sh just ports/stm32/lint
    ./run.sh just extmod/foundation-rust/lint

# Build mpy-cross.
mpy-cross:
    #!/usr/bin/env bash
    set -e

    if [ "$USE_DOCKER" = true ];
    then
        ./run.sh make -C mpy-cross/ \
                         PROG=mpy-cross-docker \
                         BUILD=build-docker
    else
        ./run.sh make -C mpy-cross/
    fi
