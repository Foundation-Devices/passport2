# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Justfile - Root-level justfile for Passport

export DOCKER_REGISTRY_BASE := ''

commit_sha := `git rev-parse HEAD`
docker_image := 'foundation-devices/firmware-builder:' + commit_sha
base_path := 'ports/stm32'
firmware_path := base_path + '/build-Passport/'

# build the docker image and then the firmware and bootloader
# build: docker-build firmware-build bootloader-build
# build: docker-build (build-bootloader "mono") (build-bootloader "color") (build-firmware "mono") (build-firmware "color")

init:
  # Ensure submodules are cloned
  git submodule update --init --recursive
  # Setup the image converter tool
  cd tools/lv_img_conv && npm install

# build the dependency docker image
build-docker:
  #!/usr/bin/env bash
  set -exo pipefail
  docker build -t ${DOCKER_REGISTRY_BASE}{{docker_image}} .

# build the firmware inside docker
build-firmware screen="mono":
  #!/usr/bin/env bash
  set -exo pipefail
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/{{base_path}} \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c 'just build {{screen}} MPY_CROSS=/usr/bin/mpy-cross'

# build the bootloader inside docker
build-bootloader screen="mono":
  #!/usr/bin/env bash
  set -exo pipefail
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/{{base_path}}/boards/Passport/bootloader \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c 'just build {{screen}}'

# build the docker image and get the tools from it
tools: build-docker cosign-tool add-secrets-tool word-list-gen-tool

# get cosign tool from built docker image
cosign-tool:
  #!/usr/bin/env bash
  set -exo pipefail
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c 'cp /usr/bin/cosign cosign'

# get add-secrets tool from built docker image
add-secrets-tool:
  #!/usr/bin/env bash
  set -exo pipefail
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c 'make -C ports/stm32/boards/Passport/tools/add-secrets'

# get word_list_gen tool from built docker image
word-list-gen-tool:
  #!/usr/bin/env bash
  set -exo pipefail
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/ports/stm32/boards/Passport/tools/word_list_gen \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c 'gcc word_list_gen.c bip39_words.c bytewords_words.c -o word_list_gen'

# run the built firmware through SHA256
verify-sha sha:
  #!/usr/bin/env bash
  sha=$(shasum -a 256 {{firmware_path}} | awk '{print $1}')

  echo -e "Expected SHA:\t{{sha}}"
  echo -e "Actual SHA:\t${sha}"
  if [ "$sha" = "{{sha}}" ]; then
    echo "Hashes match!"
  else
    echo "ERROR: Hashes DO NOT match!"
  fi

# sign the built firmware using a private key and the cosign tool
sign keypath version screen="mono": (build-firmware screen)
  #!/usr/bin/env bash
  set -exo pipefail

  SCREEN={{screen}}
  SCREEN=`echo ${SCREEN^^}`
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/{{base_path}} \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c "just cosign_filepath=build-Passport/firmware-$SCREEN.bin cosign_keypath={{keypath}} sign {{version}} {{screen}} MPY_CROSS=/usr/bin/mpy-cross"

# clean firmware build
clean:
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/{{base_path}} \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c "make clean BOARD=Passport"

# clean bootloader build
clean-bootloader:
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/{{base_path}}/boards/Passport/bootloader \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c "just clean"

# clean simulator build
clean-simulator:
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/simulator \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c "just clean"

build-simulator screen="mono":
  docker run --rm -v "$PWD":/workspace \
    -u $(id -u):$(id -g) \
    -w /workspace/simulator \
    --entrypoint bash \
    ${DOCKER_REGISTRY_BASE}{{docker_image}} \
    -c "just build {{screen}} MPY_CROSS=/usr/bin/mpy-cross"

# Run the simulator.
sim screen="mono" ext="":
  just simulator/sim {{screen}} {{ext}}

simulatordir := `pwd` + "/simulator"
# Run unit tests.
test:
  just simulator/build color
  cd ports/stm32/boards/Passport/modules/tests/; python3 -m pytest . --simulatordir={{simulatordir}}

# Lint the codebase.
lint:
  just ports/stm32/lint