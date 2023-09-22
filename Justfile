# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Justfile - Root-level Justfile for Passport

export DOCKER_IMAGE := env_var_or_default('DOCKER_IMAGE', 'foundation-devices/passport2:latest')
export DOCKER_CMD := env_var_or_default('DOCKER_CMD', 'docker')

DOCKER_RUN := if DOCKER_CMD == 'docker' { 'docker run -u $(id -u):$(id -g)' } else { 'podman run' }

# Build the docker image
build-docker:
    $DOCKER_CMD build -t ${DOCKER_IMAGE} .

# Build the firmware inside docker.
build-firmware screen="mono": mpy-cross (run-in-docker ("just ports/stm32/build " + screen))

# build the bootloader inside docker
build-bootloader screen="mono": (run-in-docker ("just ports/stm32/boards/Passport/bootloader/build " + screen))

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

tools: build-add-secrets build-cosign

# Build the add-secrets tool.
build-add-secrets: (run-in-docker "make -C ports/stm32/boards/Passport/tools/add-secrets")

# Build the cosign tool.
build-cosign: (run-in-docker "make -C ports/stm32/boards/Passport/tools/cosign")

# Sign the built firmware using a private key and the cosign tool
sign keypath version screen="mono": (build-firmware screen) (build-cosign) (run-in-docker ("just cosign_filepath=build-Passport/firmware-" + uppercase(screen) + ".bin cosign_keypath=" + keypath + " ports/stm32/sign " + version + " " + screen))

# Clean firmware build
clean: (run-in-docker "just ports/stm32/clean")

# Clean bootloader build
clean-firmware: (run-in-docker "just ports/stm32/clean")

# Clean bootloader build
clean-bootloader: (run-in-docker "just ports/stm32/boards/Passport/bootloader/clean")

# Clean simulator build
clean-simulator: (run-in-docker "just simulator/clean")

# Build simulator
build-simulator screen="mono": (run-in-docker ("just simulator/build " + screen))

# Run the simulator.
sim screen="mono" ext="":
    just simulator/sim {{screen}} {{ext}}

# Run unit tests.
test:
  just simulator/build color
  cd ports/stm32/boards/Passport/modules/tests; python3 -m pytest . --simulatordir=$(pwd)/simulator

# Lint the codebase.
lint: (run-in-docker "just ports/stm32/lint") (run-in-docker "just extmod/foundation-rust/lint")

# Hash the files
hash filepath screen="mono" output_file="":
    #!/usr/bin/env bash

    if [ "{{screen}}" != "mono" ] && [ "{{screen}}" != "color" ]; then
        echo "Screen must be either 'mono' or 'color', the default value is 'mono'."
        exit 1
    fi

    set -e
    filename=`basename {{filepath}}`
    directory=`dirname {{filepath}}`
    release_name=${filename::-13}

    # SHA256
    sha=`shasum -b -a 256 {{filepath}} | sed -rn 's/^(.*) .*$/\1/p'`
    echo "$sha" > ${directory}/${release_name}-sha256

    # MD5
    md5=`mdsum {{filepath}} | sed -rn 's/^(.*) .*$/\1/p' | xargs`
    echo "$md5" > ${directory}/${release_name}-md5

    # Build Hash
    build_hash=`cosign -t {{screen}} -p -f {{filepath}} | sed -rn 's/^FW Build Hash:    (.*)$/\1/p'`
    echo "$build_hash" > ${directory}/${release_name}-build-hash

    output="## RELEASE HASHES\n\n"

    if [ -n "{{output_file}}" ]; then
        output+="### $filename:\n\n"
    fi

    output+="SHA256: \`$sha\`\nMD5: \`$md5\`\n\nYou can check these hashes with the following commands on most operating systems:\n\n"

    output+="SHA256: \`shasum -b -a 256 $filename\`\nMD5: \`md5 $filename\` or \`mdsum $filename\` or \`md5sum $filename\`\n\n"
    output+="### DEVELOPERS ONLY\n\nBuild Hash: \`$build_hash\`"

    if [ -z "{{output_file}}" ]; then
        echo -e "$output"
        echo -e "$output" > ${directory}/${release_name}-hashes.md
    else
        echo -e "$output" > "{{output_file}}"
    fi

[private]
mpy-cross: (run-in-docker "make -C mpy-cross PROG=mpy-cross-docker BUILD=build-docker")

[private]
run-in-docker command:
    {{DOCKER_RUN}} --rm \
        -v $(pwd):/workspace \
        -w /workspace \
        -e MPY_CROSS="/workspace/mpy-cross/mpy-cross-docker" \
        --entrypoint bash \
        ${DOCKER_IMAGE} \
        -c 'export PATH=$PATH:/workspace/ports/stm32/boards/Passport/tools/cosign/x86/release;{{command}}'
