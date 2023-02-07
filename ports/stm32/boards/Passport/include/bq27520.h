// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Passport hardware build only.  It is not shared with the unix
// simulator.

#ifndef __BQ27520_H
#define __BQ27520_H

#include <stdint.h>

#include "stm32h7xx_hal.h"

// I2C 7-bit address shifted to the left by 1 bit in order to use it with the
// HAL.
#define BQ27520_I2C_ADDR (0x55 << 1)

// Standard Commands
#define BQ27520_CMD_CNTL (0x00)            // Control()
#define BQ27520_CMD_AR (0x02)              // AtRate()
#define BQ27520_CMD_ARTTE (0x04)           // AtRateTimeToEmpty()
#define BQ27520_CMD_TEMP (0x06)            // Temperature()
#define BQ27520_CMD_VOLT (0x08)            // Voltage()
#define BQ27520_CMD_FLAGS (0x0A)           // Flags()
#define BQ27520_CMD_NAC (0x0C)             // NominalAvailableCapacity()
#define BQ27520_CMD_FAC (0x0E)             // FullAvailableCapacity()
#define BQ27520_CMD_RM (0x10)              // RemainingCapacity()
#define BQ27520_CMD_FCC (0x12)             // FullChargeCapacity()
#define BQ27520_CMD_AI (0x14)              // AverageCurrent()
#define BQ27520_CMD_TTE (0x16)             // TimeToEmpty()
#define BQ27520_CMD_SI (0x18)              // StandbyCurrent()
#define BQ27520_CMD_STTE (0x1A)            // StandbyTimeToEmpty()
#define BQ27520_CMD_SOH (0x1C)             // StateOfHealth()
#define BQ27520_CMD_CC (0x1E)              // CycleCount()
#define BQ27520_CMD_SOC (0x20)             // StateOfCharge()
#define BQ27520_CMD_INSTANTANEOUSI (0x22)  // InstantaneousCurrent()
#define BQ27520_CMD_INTTEMP (0x28)         // InternalTemperature()
#define BQ27520_CMD_OpConfig (0x2C)        // OperationConfig()
#define BQ27520_CMD_DESIGN_CAPACTY (0x2E)  // DesignCapacity(()
#define BQ27520_CMD_UFRM (0x6C)            // UnfilteredRM()
#define BQ27520_CMD_FRM (0x6E)             // FilteredRM()
#define BQ27520_CMD_UFFCC (0x70)           // UnfilteredFCC()
#define BQ27520_CMD_FFCC (0x72)            // FilteredFCC()
#define BQ27520_CMD_UFSOC (0x74)           // TrueSOC()

// Extended Data Commands
#define BQ27520_EXTCMD_DATA_FLASH_CLASS (0x3E)    // DataFlashClass()
#define BQ27520_EXTCMD_DATA_FLASH_BLOCK (0x3F)    // DataFlashBlock()
#define BQ27520_EXTCMD_BLOCK_DATA (0x40)          // BlockData()
#define BQ27520_EXTCMD_BLOCK_DATA_CKSUM (0x60)    // BlockDataCheckSum()
#define BQ27520_EXTCMD_BLOCK_DATA_CONTROL (0x61)  // BlockDataControl()
#define BQ27520_EXTCMD_APPLICATION_STATUS (0x6A)  // ApplicationStatus()

// Control Command Commands
#define BQ27520_CTRLCMD_CONTROL_STATUS (0x0000)
#define BQ27520_CTRLCMD_DEVICE_TYPE (0x0001)
#define BQ27520_CTRLCMD_FW_VERSION (0x0002)
#define BQ27520_CTRLCMD_PREV_MACWRITE (0x0007)
#define BQ27520_CTRLCMD_CHEM_ID (0x0008)
#define BQ27520_CTRLCMD_OCV_CMD (0x000C)
#define BQ27520_CTRLCMD_BAT_INSERT (0x000D)
#define BQ27520_CTRLCMD_BAT_REMOVE (0x000E)
#define BQ27520_CTRLCMD_SET_HIBERNATE (0x0011)
#define BQ27520_CTRLCMD_CLEAR_HIBERNATE (0x0012)
#define BQ27520_CTRLCMD_SET_SNOOZE (0x0013)
#define BQ27520_CTRLCMD_CLEAR_SNOOZE (0x0014)
#define BQ27520_CTRLCMD_DF_VERSION (0x001F)
#define BQ27520_CTRLCMD_SEALED (0x0020)
#define BQ27520_CTRLCMD_IT_ENABLE (0x0021)
#define BQ27520_CTRLCMD_RESET (0x0041)

// Control Status Register definitions
#define BQ27520_CONTROL_STATUS_QEN (1 << 0)
#define BQ27520_CONTROL_STATUS_VOK (1 << 1)
#define BQ27520_CONTROL_STATUS_RUP_DIS (1 << 2)
#define BQ27520_CONTROL_STATUS_LDMD (1 << 3)
#define BQ27520_CONTROL_STATUS_SLEEP (1 << 4)
#define BQ27520_CONTROL_STATUS_SNOOZE (1 << 5)
#define BQ27520_CONTROL_STATUS_HIBERNATE (1 << 6)
#define BQ27520_CONTROL_STATUS_INITCOMP (1 << 7)
#define BQ27520_CONTROL_STATUS_OCVFAIL (1 << 8)
#define BQ27520_CONTROL_STATUS_OCVCMDCOMP (1 << 9)
#define BQ27520_CONTROL_STATUS_BCA (1 << 10)
#define BQ27520_CONTROL_STATUS_CCA (1 << 11)
#define BQ27520_CONTROL_STATUS_SS (1 << 13)
#define BQ27520_CONTROL_STATUS_FAS (1 << 14)

// Data Flash Subclass IDs
#define BQ27520_SUBID_CONFIGURATION_SAFETY (2)
#define BQ27520_SUBID_CONFIGURATION_CHARGE_INHIBIT_CFG (32)
#define BQ27520_SUBID_CONFIGURATION_CHARGE (34)
#define BQ27520_SUBID_CONFIGURATION_CHARGE_TERMINATION (36)
#define BQ27520_SUBID_CONFIGURATION_DATA (48)
#define BQ27520_SUBID_CONFIGURATION_DISCHARGE (49)
#define BQ27520_SUBID_CONFIGURATION_REGISTERS (64)
#define BQ27520_SUBID_CONFIGURATION_POWER (68)
#define BQ27520_SUBID_SYSTEM_DATA_MANUFACURER_INFO (57)
#define BQ27520_SUBID_GAS_GAUGING_IT_CFG (80)
#define BQ27520_SUBID_GAS_GAUGING_CURRENT_THRESHOLDS (81)
#define BQ27520_SUBID_GAS_GAUGING_STATE (82)
#define BQ27520_SUBID_OCV_TABLE_OCV_VA0_TABLE (83)
#define BQ27520_SUBID_OCV_TABLE_OCV_VA1_TABLE (84)
#define BQ27520_SUBID_DEFAULT_RA_TABLES_DEF0_RA (87)
#define BQ27520_SUBID_DEFAULT_RA_TABLES_DEF1_RA (88)
#define BQ27520_SUBID_RA_TABLES_PACK0_RA (91)
#define BQ27520_SUBID_RA_TABLES_PACK1_RA (92)
#define BQ27520_SUBID_RA_TABLES_PACK0_RAX (93)
#define BQ27520_SUBID_RA_TABLES_PACK1_RAX (94)
#define BQ27520_SUBID_CALIBRATION_DATA (104)
#define BQ27520_SUBID_CALIBRATION_TEMP_MODEL (106)
#define BQ27520_SUBID_CALIBRATION_TEMP_CURRENT (107)
#define BQ27520_SUBID_SECURITY_CODES (112)

// Status Register definitions
#define BQ27520_SR_DSG (1 << 0)
#define BQ27520_SR_SYSDOWN (1 << 1)
#define BQ27520_SR_SOC1 (1 << 2)
#define BQ27520_SR_BAT_DET (1 << 3)
#define BQ27520_SR_WAIT_ID (1 << 4)
#define BQ27520_SR_OCV_GD (1 << 5)
#define BQ27520_SR_CHG (1 << 8)
#define BQ27520_SR_FC (1 << 9)
#define BQ27520_SR_XCHG (1 << 10)
#define BQ27520_SR_CHG_INH (1 << 11)
#define BQ27520_SR_CALMODE (1 << 12)
#define BQ27520_SR_OTD (1 << 13)
#define BQ27520_SR_OTC (1 << 14)

// Operation Config Register definitions
#define BQ27520_OPCONFIG_TEMPS (1 << 0)
#define BQ27520_OPCONFIG_BATL_POL (1 << 1)
#define BQ27520_OPCONFIG_BATG_POL (1 << 2)
#define BQ27520_OPCONFIG_SOCI_POL (1 << 3)
#define BQ27520_OPCONFIG_RMFCC (1 << 4)
#define BQ27520_OPCONFIG_SLEEP (1 << 5)
#define BQ27520_OPCONFIG_IDSELEN (1 << 6)
#define BQ27520_OPCONFIG_INT_FOCV (1 << 7)
#define BQ27520_OPCONFIG_RSNS0 (1 << 8)
#define BQ27520_OPCONFIG_RSNS1 (1 << 9)
#define BQ27520_OPCONFIG_IWAKE (1 << 10)
#define BQ27520_OPCONFIG_PFC_CFG0 (1 << 11)
#define BQ27520_OPCONFIG_PFC_CFG1 (1 << 12)
#define BQ27520_OPCONFIG_INT_BREM (1 << 13)
#define BQ27520_OPCONFIG_BATG_OVR (1 << 14)
#define BQ27520_OPCONFIG_RESCAP (1 << 15)

#define BQ27520_OPCONFIG_RESET                                                                              \
    (BQ27520_OPCONFIG_TEMPS | BQ27520_OPCONFIG_BATL_POL | BQ27520_OPCONFIG_RMFCC | BQ27520_OPCONFIG_SLEEP | \
     BQ27520_OPCONFIG_IDSELEN | BQ27520_OPCONFIG_RSNS0 | BQ27520_OPCONFIG_PFC_CFG0)

// Control(): DEVICE_TYPE
#define BQ27520_DEVICE_TYPE (0x0520)
#define BQ27520_DEVICE_TYPE_WAIT_US (2500)

// Unseal Keys
#define BQ27520_UNSEAL_KEY0 (0x0414)
#define BQ27520_UNSEAL_KEY1 (0x3672)

// Battery capacity read types.
typedef enum {
    BQ27520_CAPACITY_NOMINAL_AVAILABLE = BQ27520_CMD_NAC,
    BQ27520_CAPACITY_FULL_AVAILABLE    = BQ27520_CMD_FAC,
    BQ27520_CAPACITY_REMAINING         = BQ27520_CMD_RM,
    BQ27520_CAPACITY_FULL_CHARGE       = BQ27520_CMD_FCC,
    BQ27520_CAPACITY_DESIGN            = BQ27520_CMD_DESIGN_CAPACTY,
} bq27520_capacity_t;

#define BQ27520_IS_CAPACITY(cap)                                                                \
    ((cap) == BQ27520_CAPACITY_NOMINAL_AVAILABLE || (cap) == BQ27520_CAPACITY_FULL_AVAILABLE || \
     (cap) == BQ27520_CAPACITY_REMAINING || (cap) == BQ27520_CAPACITY_FULL_CHARGE || (cap) == BQ27520_CAPACITY_DESIGN)

// State-of-Health status.
typedef enum {
    BQ27520_SOH_NOT_VALID     = 0x00,
    BQ27520_SOH_INSTANT_READY = 0x01,
    BQ27520_SOH_INITIAL_READY = 0x02,
    BQ27520_SOH_READY         = 0x03,
} bq27520_soh_status_t;

#define BQ27520_IS_SOH(soh)                                                                                        \
    ((soh) == BQ27520_SOH_NOT_VALID || (soh) == BQ27520_SOH_INSTANT_READY || (soh) == BQ27520_SOH_INITIAL_READY || \
     (soh) == BQ27520_SOH_READY)

// Data flash buffer
typedef struct {
    uint8_t class;
    uint8_t block;
    bool    has_data;
    uint8_t data[32];
} bq27520_flash_buf_t;

// SOC_INT interrupt callback. The parameter is the pulse width in milliseconds.
typedef void (*bq27520_soc_int_cb_t)(uint32_t);

// Initialize BQ27520 Fuel Gauge Driver.
void bq27520_init(void);

// De-initialize BQ27520 driver.
void bq27520_deinit(void);

// Register interrupt handler for SOC_INT.
void bq27520_register_soc_int_cb(bq27520_soc_int_cb_t cb);

// Check if the fuel gauge is present and the device type is correct.
HAL_StatusTypeDef bq27520_probe(void);

// Checks if the fuel gauge is sealed.
HAL_StatusTypeDef bq27520_is_sealed(bool* is_sealed);

// Seal the fuel gauge.
HAL_StatusTypeDef bq27520_seal(void);

// Unseal the fuel gauge.
HAL_StatusTypeDef bq27520_unseal(void);

/// Read data flash block.
HAL_StatusTypeDef bq27520_read_flash_block(bq27520_flash_buf_t* buf);

/// Write data flash block.
HAL_StatusTypeDef bq27520_write_flash_block(bq27520_flash_buf_t* buf);

// Reset the fuel gauge.
HAL_StatusTypeDef bq27520_reset();

// Read the AtRate() value. In mAh.
HAL_StatusTypeDef bq27520_read_atrate(int16_t* current);

// Write the AtRate() value. In mAh.
HAL_StatusTypeDef bq27520_write_atrate(int16_t current);

// Read the Time-to-Empty calculated from the last written AtRate().
// In minutes.
//
// A value of 65535 means that AtRate() is 0.
HAL_StatusTypeDef bq27520_read_atrate_time_to_empty(uint16_t* tte);

// Read battery temperature. In units of 0.1 K.
//
// Depending on the configuration this can be:
// - Internal temperature of the fuel gauge.
// - Temperature sensed on TS.
// - A previous value written if on manual mode.
HAL_StatusTypeDef bq27520_read_temp(uint16_t* temp);

// Read battery voltage. In millivolts.
HAL_StatusTypeDef bq27520_read_volt(uint16_t* voltage);

// Read fuel gauge flags.
HAL_StatusTypeDef bq27520_read_flags(uint16_t* flags);

// Checks if the battery is detected.
HAL_StatusTypeDef bq27520_is_battery_detected(bool* is_detected);

// Read battery capacity. In mAh.
HAL_StatusTypeDef bq27520_read_capacity(bq27520_capacity_t type, uint16_t* capacity);

// Read average current. In mA.
HAL_StatusTypeDef bq27520_read_average_current(int16_t* current);

// Read Time-To-Empty. In minutes.
HAL_StatusTypeDef bq27520_read_time_to_empty(uint16_t* tte);

// Read standby current. In mAh.
HAL_StatusTypeDef bq27520_read_standby_current(int16_t* current);

// Read Time-to-Empty in standby. In minutes.
HAL_StatusTypeDef bq27520_read_standby_time_to_empty(uint16_t* tte);

// Read State-of-Health. In percentage (0-100 %).
HAL_StatusTypeDef bq27520_read_state_of_health(uint8_t* soh, bq27520_soh_status_t* status);

// Read cycle count.
HAL_StatusTypeDef bq27520_read_cycle_count(uint16_t* cc);

// Read State-of-Charge. In percentage (0-100%).
HAL_StatusTypeDef bq27520_read_soc(uint16_t* soc);

// Read instantaneous current. In mA.
HAL_StatusTypeDef bq27520_read_instantaneous_current(int16_t* current);

// Read internal temperature. In units of 0.1 K
HAL_StatusTypeDef bq27520_read_inttemp(uint16_t* temperature);

// Read OpConfig register.
HAL_StatusTypeDef bq27520_read_opconfig(uint16_t* opconfig);

/// SOC_INT pin interrupt service routine.
void bq27520_soc_int_isr(void);

#endif  //__BQ27520_H
