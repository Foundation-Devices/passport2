#!/usr/bin/env bash
#
# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Generate bindings of STM32H7xx_HAL_Driver using rust-bindgen.
#
# To generate bindings:
#
#   ./bindgen.sh
#
# To check if bindings need to be re-generated:
#
#   ./bindgen.sh -c

CC=arm-none-eabi-gcc

usage() {
  echo "Usage: $0 [-c]"
  exit 1
}

check=false
while getopts "c" o; do
  case "${o}" in
    c)
    check=true
    ;;
    *)
    usage
    ;;
  esac
done

# From: https://stackoverflow.com/a/246128
SOURCE=${BASH_SOURCE[0]}
while [ -L "$SOURCE" ]
do
  DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )
  SOURCE=$(readlink "$SOURCE")
  [[ $SOURCE != /* ]] && SOURCE=$DIR/$SOURCE
done
DIR=$( cd -P "$( dirname "$SOURCE" )" >/dev/null 2>&1 && pwd )

system_include_directories=$($CC -v -xc -E /dev/null 2>&1 | awk -f "$DIR/includes.awk")

clang_arguments='--target=arm-none-eabi -mcpu=cortex-m7'
for includedir in ${system_include_directories}
do
  clang_arguments+=" -isystem $includedir"
done

clang_arguments+=" \
-I$DIR/../../../lib/cmsis/inc \
-I$DIR/../../../lib/stm32lib/CMSIS/STM32H7xx/Include \
-I$DIR/../../../lib/stm32lib/STM32H7xx_HAL_Driver/Inc \
-I$DIR/../../../ports/stm32/boards/Passport \
-DSTM32H753xx \
"

if [ "$check" = true ]
then
  output=$(mktemp)
else
  output=$DIR/src/gen.rs
fi

# NOTE:
#
# --allowlist-item '^.*_BASE$': this is for the peripheral base addresses.
# Should be a cmsis-device-h7-sys crate.
echo "BINDGEN_EXTRA_CLANG_ARGS=$clang_arguments"
echo "generating bindings: $output"
BINDGEN_EXTRA_CLANG_ARGS="$clang_arguments" bindgen $DIR/bindings.h \
    --verbose \
    --rust-target 1.73 \
    --use-core \
    --no-doc-comments \
    --default-enum-style moduleconsts \
    --sort-semantically \
    --allowlist-item '^.*_BASE$' \
    --allowlist-function '^HAL_.*$' \
    --output $output

# Format the resulting file.
rustfmt --config-path "$DIR/.." $output

if [ "$check" = true ]
then
  echo "verifying if bindings need to be re-generated."
  if diff "$DIR/src/gen.rs" "$output" >/dev/null
  then
    echo "done."
  else
    diff "$DIR/src/gen.rs" "$output"
    echo "error: bindings need to be re-generated!"
    exit 1
  fi
else
  echo "bindings up to date."
fi
