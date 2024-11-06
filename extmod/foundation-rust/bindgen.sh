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
-I$DIR/../../lib/cmsis/inc \
-I$DIR/../../lib/stm32lib/CMSIS/STM32H7xx/Include \
-I$DIR/../../lib/stm32lib/STM32H7xx_HAL_Driver/Inc \
-I$DIR/../../ports/stm32/boards/Passport \
-DSTM32H753xx \
"

if [ "$check" = true ]
then
  stm32h7xx_hal_driver_sys_output=$(mktemp)
  cmsis_device_h7_sys_output=$(mktemp)
else
  stm32h7xx_hal_driver_sys_output=$DIR/stm32h7xx-hal-driver-sys/src/gen.rs
  cmsis_device_h7_sys_output=$DIR/cmsis-device-h7-sys/src/gen.rs
fi

echo "BINDGEN_EXTRA_CLANG_ARGS=$clang_arguments"
export BINDGEN_EXTRA_CLANG_ARGS="$clang_arguments"

bindgen_arguments="\
--verbose \
--rust-target 1.73 \
--use-core \
--no-doc-comments \
--default-enum-style moduleconsts \
--sort-semantically \
--no-recursive-allowlist \
--rustfmt-configuration-file $DIR/.rustfmt.toml \
"

echo "generating stm32h7xx-hal-driver-sys bindings: $stm32h7xx_hal_driver_sys_output"
bindgen "$DIR/stm32h7xx-hal-driver-sys/bindings.h" \
        $bindgen_arguments \
        --raw-line 'use cmsis_device_h7_sys::*;' \
        --allowlist-item '^HAL_.*$' \
        --allowlist-type '^.*_HandleTypeDef$' \
        --allowlist-type '^.*InitTypeDef$' \
        --allowlist-type '^.*_StateTypeDef$' \
        --allowlist-type 'USB_OTG_CfgTypeDef' \
        --allowlist-type 'MDMA_LinkNodeTypeDef' \
        --allowlist-type 'MDMA_LinkNodeConfTypeDef' \
        --allowlist-type 'ADC_OversamplingTypeDef' \
        --allowlist-type 'ADC_AnalogWDGConfTypeDef' \
        --allowlist-type 'ADC_MultiModeTypeDef' \
        --allowlist-type 'ADC_ChannelConfTypeDef' \
        --allowlist-type 'ADC_InjOversamplingTypeDef' \
        --allowlist-type 'DAC_SampleAndHoldConfTypeDef' \
        --allowlist-type 'DCMI_CodesInitTypeDef' \
        --allowlist-type 'FDCAN_GlobalTypeDef' \
        --allowlist-type 'FDCAN_MsgRamAddressTypeDef' \
        --allowlist-type 'FDCAN_TTOperationStatusTypeDef' \
        --allowlist-type 'FDCAN_TriggerTypeDef' \
        --allowlist-type 'FDCAN_TT_ConfigTypeDef' \
        --allowlist-type 'FDCAN_ErrorCountersTypeDef' \
        --allowlist-type 'FDCAN_ProtocolStatusTypeDef' \
        --allowlist-type 'FDCAN_HpMsgStatusTypeDef' \
        --allowlist-type 'FDCAN_RxHeaderTypeDef' \
        --allowlist-type 'FDCAN_TxHeaderTypeDef' \
        --allowlist-type 'FDCAN_TxEventFifoTypeDef' \
        --allowlist-type 'FDCAN_FilterTypeDef' \
        --allowlist-type 'FDCAN_ClkCalUnitTypeDef' \
        --allowlist-type 'DCMI_SyncUnmaskTypeDef' \
        --allowlist-type 'DAC_ChannelConfTypeDef' \
        --allowlist-type 'GPIO_PinState' \
        --allowlist-type 'PCD_(BCD|LPM)_MsgTypeDef' \
        --allowlist-type 'FlagStatus' \
        --allowlist-type 'FunctionalState' \
        --allowlist-type 'UART_WakeUpTypeDef' \
        --allowlist-type 'TIM_SlaveConfigTypeDef' \
        --allowlist-type 'TIM_ClockConfigTypeDef' \
        --allowlist-type 'TIM_ClearInputConfigTypeDef' \
        --allowlist-type 'TIMEx_BreakInputConfigTypeDef' \
        --allowlist-type 'TIM_BreakDeadTimeConfigTypeDef' \
        --allowlist-type '^FMC_SDRAM.*$' \
        --allowlist-type 'TIM_MasterConfigTypeDef' \
        --allowlist-type 'RTC_(Alarm|Date|Tamper|Time)TypeDef' \
        --allowlist-type 'RCC_CRSSynchroInfoTypeDef' \
        --allowlist-type 'PLL[123]_ClocksTypeDef' \
        --allowlist-type '^PWREx_.*$' \
        --allowlist-type 'PWR_PVDTypeDef' \
        --allowlist-type '^HCD_.*$' \
        --allowlist-type 'ADC_InjectionConfigTypeDef' \
        --allowlist-type 'PCD_TypeDef' \
        --allowlist-type 'PCD_EPTypeDef' \
        --allowlist-type 'ADC_InjectionConfTypeDef' \
        --allowlist-type 'USB_OTG_EPTypeDef' \
        --allowlist-type 'USB_OTG_GlobalTypeDef' \
        --allowlist-type 'USB_OTG_HCTypeDef' \
        --allowlist-type 'USB_OTG_HCStateTypeDef' \
        --allowlist-type 'USB_OTG_URBStateTypeDef' \
        --output "$stm32h7xx_hal_driver_sys_output"

echo "generating cmsis-device-h7-sys bindings: $cmsis_device_h7_sys_output"
bindgen "$DIR/cmsis-device-h7-sys/bindings.h" \
        $bindgen_arguments \
        --allowlist-item '^.*_BASE$' \
        --allowlist-item '^RCC_.*$' \
        --allowlist-type 'IRQn_Type' \
        --allowlist-type '^.*_TypeDef$' \
        --output "$cmsis_device_h7_sys_output"

if [ "$check" = true ]
then
  echo "verifying if bindings need to be re-generated."

  diff_output=$(diff "$DIR/stm32h7xx-hal-driver-sys/src/gen.rs" "$stm32h7xx_hal_driver_sys_output")
  if [ $? -ne 0 ]
  then
    echo "$diff_output"
    echo "error: bindings need to be re-generated!"
    exit 1
  fi

  diff_output=$(diff "$DIR/cmsis-device-h7-sys/src/gen.rs" "$cmsis_device_h7_sys_output")
  if [ "$?" -ne 0 ]
  then
    echo "$diff_output"
    echo "error: bindings need to be re-generated!"
    exit 1
  fi
else
  echo "bindings up to date."
fi
