// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: BSD-3-Clause

#include <string.h>
#include <stdbool.h>

#include "bq27520.h"
#include "i2c-init.h"

#ifdef PASSPORT_BOOTLOADER
#include "delay.h"

#define DELAY_US(t) delay_us(t)
#else
#include "py/mphal.h"

#define DELAY_US(t) mp_hal_delay_us(t)
#endif

#ifndef BQ27520_DEBUG
#define BQ27520_DEBUG 0
#endif

#if BQ27520_DEBUG
#include <stdio.h>

#define DEBUG(f, ...) printf("[bq27520] %s: " f "\n", __func__, ##__VA_ARGS__)
#else
#define DEBUG(f, ...) \
    do {              \
    } while (0)
#endif  // BQ27520_DEBUG

// Execute the function `f`and return if an error occurs.
#define EXEC_RET(f)                   \
    do {                              \
        HAL_StatusTypeDef _r;         \
        if ((_r = f) != HAL_OK) {     \
            DEBUG("ret=%d", (int)_r); \
            return _r;                \
        }                             \
    } while (0)

// Check that the pointer `p` is not NULL and if it's return an error.
#define CHECK_PTR(p)               \
    do {                           \
        if ((p) == NULL) {         \
            DEBUG("null pointer"); \
            return HAL_ERROR;      \
        }                          \
    } while (0)

static uint32_t _soc_int_pulse_start_tick = 0;
static uint32_t _soc_int_pulse_end_tick   = 0;

static bq27520_soc_int_cb_t _soc_int_cb = NULL;

// Fuel gauge order to host order.
static inline uint16_t _bqtoh(uint8_t* src) {
    return (uint16_t)(src[1] << 8) | (uint16_t)(src[0]);
}

// Host order to fuel gauge order.
static inline void _htobq(uint16_t src, uint8_t* dst) {
    dst[0] = (uint8_t)(src & 0x00FFU);
    dst[1] = (uint8_t)((src >> 8) & 0x00FF);
}

static HAL_StatusTypeDef _bq27520_read(uint8_t base_addr, uint8_t* data, uint8_t len) {
    // NOTE: using incremental reads.
    EXEC_RET(HAL_I2C_Mem_Read(&g_hi2c2, BQ27520_I2C_ADDR, base_addr, I2C_MEMADD_SIZE_8BIT, data, len, HAL_MAX_DELAY));
    DELAY_US(66);

    return HAL_OK;
}

static HAL_StatusTypeDef _bq27520_write(uint16_t base_addr, uint8_t* data, uint8_t len) {
    // NOTE: using individual writes. Required for 400 kHz, also works on 100 kHz.
    for (uint8_t i = 0; i < len; i++) {
        EXEC_RET(HAL_I2C_Mem_Write(&g_hi2c2, BQ27520_I2C_ADDR, base_addr + i, I2C_MEMADD_SIZE_8BIT, &data[i],
                                   sizeof(uint8_t), HAL_MAX_DELAY));
        // NOTE: Doesn't matter what the datasheet says, the 66 us bus free
        // time doesn't work, for unknown reasons. The initial thought was that
        // the wrong value was being written, but after a printf of each
        // transfer and single stepping through code that reason was discarded,
        // however, when using a printf everything worked fine, so there was
        // something wrong with the write timing. I measured the time a printf
        // call took with the provided arguments and it was around 1700
        // microseconds plus the 66 "bus free" time, that's the reason for a
        // 1766 microseconds bus free time. It adds up.
        //
        // On another related topic, the I2C frequency is around 370 kHz
        // (measured with a Logic Analyzer), so we don't know if that bus free
        // time might only work with 400 kHz. I guess we'll never know. The I2C
        // timing registers are properly calculated but the HSE crystal has
        // around 5000 ppm (+/- 0.5%) deviation, so that might be why the drift
        // from 400 kHz to 370 kHz.
        //
        // TODO(jeandudey): Try using HSI or another clock source to reach
        // 400 kHz.
        //
        // Anyway, if it works, it works. Thanks for coming to my TED Talk.
        DELAY_US(1766);
    }

    return HAL_OK;
}

static HAL_StatusTypeDef _bq27520_control_read(uint16_t cmd, uint8_t* data, uint32_t delay_in_us) {
    CHECK_PTR(data);

    uint8_t tmp[2] = {0};
    _htobq(cmd, tmp);

    EXEC_RET(_bq27520_write(BQ27520_CMD_CNTL, tmp, sizeof(tmp)));
    DELAY_US(delay_in_us);
    //uint32_t start = mp_hal_ticks_us();
    //for (int i = 0; i < 10; i++) {
    EXEC_RET(_bq27520_read(BQ27520_CMD_CNTL, data, sizeof(uint8_t) * 2));
    //    uint32_t end = mp_hal_ticks_us();
    //    printf("%02x%02x=%lu us\n", data[1], data[0], end - start);
    //}

    return HAL_OK;
}

static HAL_StatusTypeDef _bq27520_control_write(uint16_t cmd) {
    uint8_t tmp[2] = {0};
    _htobq(cmd, tmp);

    return _bq27520_write(BQ27520_CMD_CNTL, tmp, sizeof(tmp));
}

static uint8_t _bq27520_checksum(bq27520_flash_buf_t* buf) {
    uint8_t sum = 0;

    for (int i = 0; i < sizeof(buf->data); i++) {
        sum += buf->data[i];
    }
    sum &= 0xFF;

    return 0xFF - sum;
}

void bq27520_init(void) {
    i2c_init();
}

void bq27520_deinit(void) {
    HAL_GPIO_DeInit(GPIOE, GPIO_PIN_9 | GPIO_PIN_10);
}

void bq27520_register_soc_int_cb(bq27520_soc_int_cb_t cb) {
    _soc_int_cb = cb;
}

HAL_StatusTypeDef bq27520_probe(void) {
    uint8_t  tmp[2]      = {0};
    uint16_t device_type = 0;

    EXEC_RET(_bq27520_control_read(BQ27520_CTRLCMD_DEVICE_TYPE, tmp, BQ27520_DEVICE_TYPE_WAIT_US));
    device_type = _bqtoh(tmp);
    DEBUG("DEVICE_TYPE: %04x", (unsigned)device_type);

    if (device_type != BQ27520_DEVICE_TYPE) {
        DEBUG("invalid type");
        return HAL_ERROR;
    }

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_is_sealed(bool* is_sealed) {
    CHECK_PTR(is_sealed);

    if (is_sealed == NULL) {
        return HAL_ERROR;
    }

    uint8_t tmp[2] = {0};
    EXEC_RET(_bq27520_control_read(BQ27520_CTRLCMD_CONTROL_STATUS, tmp, 2500));

    uint16_t control_status = _bqtoh(tmp);
    *is_sealed              = (control_status & BQ27520_CONTROL_STATUS_SS) ? true : false;
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_seal(void) {
    DEBUG("sealing");
    return _bq27520_control_write(BQ27520_CTRLCMD_SEALED);
}

HAL_StatusTypeDef bq27520_unseal(void) {
    DEBUG("unsealing");
    EXEC_RET(_bq27520_control_write(BQ27520_UNSEAL_KEY0));
    EXEC_RET(_bq27520_control_write(BQ27520_UNSEAL_KEY1));

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_flash_block(bq27520_flash_buf_t* buf) {
    buf->has_data = false;

    // Write 0x00 to BlockDataControl() to enable BlockData() access. Requires
    // device to be UNSEALED.
    uint8_t tmp = 0x00;
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_BLOCK_DATA_CONTROL, &tmp, sizeof(tmp)));

    // Set DataFlashClass() to read.
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_DATA_FLASH_CLASS, &buf->class, sizeof(buf->class)));

    HAL_Delay(1);

    // Set DataFlashBlock() to read.
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_DATA_FLASH_BLOCK, &buf->block, sizeof(buf->block)));

    // Read BlockData()
    EXEC_RET(_bq27520_read(BQ27520_EXTCMD_BLOCK_DATA, buf->data, sizeof(buf->data)));

    uint8_t checksum = 0;
    EXEC_RET(_bq27520_read(BQ27520_EXTCMD_BLOCK_DATA_CKSUM, &checksum, sizeof(checksum)));

    if (checksum != _bq27520_checksum(buf)) {
        DEBUG("could not read block, invalid checksum: stored=%02x calculated=%02x", (unsigned)checksum,
              (unsigned)_bq27520_checksum(buf));
        return HAL_ERROR;
    }

    buf->has_data = true;
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_write_flash_block(bq27520_flash_buf_t* buf) {
    if (!buf->has_data) {
        return HAL_ERROR;
    }

    // Write 0x00 to BlockDataControl() to enable BlockData() access. Requires
    // device to be UNSEALED.
    uint8_t tmp = 0x00;
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_BLOCK_DATA_CONTROL, &tmp, sizeof(tmp)));

    // Set DataFlashClass() to read.
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_DATA_FLASH_CLASS, &buf->class, sizeof(buf->class)));

    // Set DataFlashBlock() to read.
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_DATA_FLASH_BLOCK, &buf->block, sizeof(buf->block)));

    HAL_Delay(1);

    // Write BlockData()
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_BLOCK_DATA, buf->data, sizeof(buf->data)));

    // Write BlockDataCheckSum()
    uint8_t checksum = _bq27520_checksum(buf);
    EXEC_RET(_bq27520_write(BQ27520_EXTCMD_BLOCK_DATA_CKSUM, &checksum, sizeof(checksum)));

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_reset() {
    return _bq27520_control_write(BQ27520_CTRLCMD_RESET);
}

HAL_StatusTypeDef bq27520_read_atrate(int16_t* current) {
    CHECK_PTR(current);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_AR, tmp, sizeof(tmp)));
    *current = (int16_t)_bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_write_atrate(int16_t current) {
    uint8_t tmp[2] = {0};

    _htobq((uint16_t)current, tmp);
    return _bq27520_write(BQ27520_CMD_AR, tmp, sizeof(tmp));
}

HAL_StatusTypeDef bq27520_read_atrate_time_to_empty(uint16_t* tte) {
    CHECK_PTR(tte);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_ARTTE, tmp, sizeof(tmp)));
    *tte = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_temp(uint16_t* temp) {
    CHECK_PTR(temp);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_TEMP, tmp, sizeof(tmp)));
    *temp = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_volt(uint16_t* voltage) {
    CHECK_PTR(voltage);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_VOLT, tmp, sizeof(tmp)));
    *voltage = _bqtoh(tmp);
    if (*voltage > 6000) {
        *voltage = 0;
        return HAL_ERROR;
    }

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_flags(uint16_t* flags) {
    CHECK_PTR(flags);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_FLAGS, tmp, sizeof(tmp)));
    *flags = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_is_battery_detected(bool* is_detected) {
    CHECK_PTR(is_detected);

    uint16_t flags = 0;
    EXEC_RET(bq27520_read_flags(&flags));

    *is_detected = flags & BQ27520_SR_BAT_DET;

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_capacity(bq27520_capacity_t type, uint16_t* capacity) {
    CHECK_PTR(capacity);

    uint8_t tmp[2] = {0};

    if (!BQ27520_IS_CAPACITY(type)) {
        DEBUG("invalid capacity type: %02x", (unsigned)type);
        return HAL_ERROR;
    }

    EXEC_RET(_bq27520_read(type, tmp, sizeof(tmp)));
    *capacity = _bqtoh(tmp);
    DEBUG("capacity=%u mAh (%04x)", (unsigned)*capacity, (unsigned)*capacity);

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_average_current(int16_t* current) {
    CHECK_PTR(current);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_AI, tmp, sizeof(tmp)));
    *current = (int16_t)_bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_time_to_empty(uint16_t* tte) {
    CHECK_PTR(tte);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_TTE, tmp, sizeof(tmp)));
    *tte = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_standby_current(int16_t* current) {
    CHECK_PTR(current);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_SI, tmp, sizeof(tmp)));
    *current = (int16_t)_bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_standby_time_to_empty(uint16_t* tte) {
    CHECK_PTR(tte);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_STTE, tmp, sizeof(tmp)));
    *tte = (int16_t)_bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_state_of_health(uint8_t* soh, bq27520_soh_status_t* status) {
    CHECK_PTR(soh);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_SOH, tmp, sizeof(tmp)));
    if (tmp[0] > 100) {
        DEBUG("invalid SOH: %02x", (unsigned)tmp[0]);
        *soh    = 0;
        *status = 0;
        return HAL_ERROR;
    }
    *soh = tmp[0];

    if (!BQ27520_IS_SOH(tmp[1])) {
        DEBUG("invalid SOH status: %02x", (unsigned)tmp[1]);
        *soh    = 0;
        *status = 0;
        return HAL_ERROR;
    }
    *status = tmp[1];

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_cycle_count(uint16_t* cc) {
    CHECK_PTR(cc);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_CC, tmp, sizeof(tmp)));
    *cc = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_soc(uint16_t* soc) {
    CHECK_PTR(soc);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_SOC, tmp, sizeof(tmp)));
    *soc = _bqtoh(tmp);
    if (*soc > 100) {
        DEBUG("invalid SOC: %04x\n", (unsigned)*soc);
        return HAL_ERROR;
    }

    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_instantaneous_current(int16_t* current) {
    CHECK_PTR(current);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_INSTANTANEOUSI, tmp, sizeof(tmp)));
    *current = (int16_t)_bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_inttemp(uint16_t* temperature) {
    CHECK_PTR(temperature);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_INTTEMP, tmp, sizeof(tmp)));
    *temperature = _bqtoh(tmp);
    return HAL_OK;
}

HAL_StatusTypeDef bq27520_read_opconfig(uint16_t* opconfig) {
    CHECK_PTR(opconfig);

    uint8_t tmp[2] = {0};

    EXEC_RET(_bq27520_read(BQ27520_CMD_OpConfig, tmp, sizeof(tmp)));
    *opconfig = _bqtoh(tmp);
    DEBUG("opconfig=%04x", (unsigned)*opconfig);
    return HAL_OK;
}

// SOC_INT interrupt service routine.
//
// The external interrupt should be configured to trigger on both rising and
// falling edges to measure the "pulse width" in milliseconds.
void bq27520_soc_int_isr(void) {
    // Nothing to do if we don't have a callback. Reset tick values to the
    // default if the callback gets removed in between interrupts.
    if (_soc_int_cb == NULL) {
        _soc_int_pulse_start_tick = 0;
        _soc_int_pulse_end_tick   = 0;
        return;
    }

    // Measure when the pulse started.
    if (_soc_int_pulse_start_tick == 0) {
        _soc_int_pulse_start_tick = HAL_GetTick();
        return;
    }

    // Measure when the pulse ends.
    if (_soc_int_pulse_end_tick == 0) {
        _soc_int_pulse_end_tick = HAL_GetTick();
    }

    uint32_t pulse_width = _soc_int_pulse_end_tick - _soc_int_pulse_start_tick;
    if (pulse_width == 0 || pulse_width > 450) {
        pulse_width = 0;
        DEBUG("pulse width is out of bounds=%lu\n", pulse_width);
    }
    // SAFETY: the guard in the top makes sure that this is not NULL.
    _soc_int_cb(pulse_width);

    _soc_int_pulse_start_tick = 0;
    _soc_int_pulse_end_tick   = 0;
}