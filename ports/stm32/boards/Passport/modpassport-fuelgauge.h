// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#ifdef HAS_FUEL_GAUGE

#include <stdio.h>

#include "py/obj.h"
#include "py/runtime.h"
#include "py/gc.h"

#include "extint.h"
#include "pins.h"

#include "bq27520.h"

#define CUSTOM_BQ27520_OPCONFIG ((BQ27520_OPCONFIG_RESET & ~BQ27520_OPCONFIG_TEMPS))

// Execute a BQ27520 driver function and raise an exception on error.
#define EXEC_RAISE(f)                                                                              \
    do {                                                                                           \
        HAL_StatusTypeDef _ret = 0;                                                                \
        if ((_ret = f) != HAL_OK) {                                                                \
            mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Could not read Fuel Gauge value")); \
            return mp_const_none;                                                                  \
        }                                                                                          \
    } while (0)

STATIC void                             mod_passport_fuelgauge_soc_int_driver_cb(uint32_t pulse_width);
STATIC const mp_obj_fun_builtin_fixed_t mod_passport_fuelgauge_soc_int_irq_callback_obj;
STATIC mp_obj_t                         mod_passport_fuelgauge_user_soc_int_callback_obj;
STATIC uint16_t                         mod_passport_fuelgauge_design_capacity = 0;

/// package: passport.fuelgauge

/// def init(design_capacity: int) -> None:
///     """
///     Initialize module.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_init(mp_obj_t design_capacity_obj) {
    mp_int_t design_capacity = mp_obj_get_int(design_capacity_obj);

    if ((design_capacity > 65535) || (design_capacity < 0)) {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid design capacity value"));
    }

    bq27520_init();

    extint_register((mp_obj_t)MICROPY_HW_BQ27520_SOC_INT_PIN, GPIO_MODE_IT_RISING_FALLING, GPIO_NOPULL,
                    (mp_obj_t)&mod_passport_fuelgauge_soc_int_irq_callback_obj, true);

    mod_passport_fuelgauge_user_soc_int_callback_obj = mp_const_none;
    mod_passport_fuelgauge_design_capacity           = design_capacity;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_fuelgauge_init_obj, mod_passport_fuelgauge_init);

/// def probe() -> boolean:
///     """
///     Checks if the fuel gauge is present.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_probe(void) {
    HAL_StatusTypeDef status = 0;
    if ((status = bq27520_probe()) != HAL_OK) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_probe_obj, mod_passport_fuelgauge_probe);

/// def is_configured() -> boolean:
///     """
///     Checks if the fuel gauge is configured properly.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_is_configured(void) {
    uint16_t tmp = 0;

    EXEC_RAISE(bq27520_read_opconfig(&tmp));
    if (tmp != CUSTOM_BQ27520_OPCONFIG) {
        return mp_const_false;
    }

    EXEC_RAISE(bq27520_read_capacity(BQ27520_CAPACITY_DESIGN, &tmp));
    if (tmp != mod_passport_fuelgauge_design_capacity) {
        return mp_const_false;
    }

    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_is_configured_obj, mod_passport_fuelgauge_is_configured);

/// def configure() -> None:
///     """
///     Configure the fuel gauge. Leaves fuel gauge unsealed.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_configure(void) {
#if 0
    bq27520_flash_buf_t tmp = {0};

    EXEC_RAISE(bq27520_unseal());

    // Data sublass
    tmp.class = 48;
    tmp.block = 0;
    memset(tmp.data, 0, sizeof(tmp.data));
    tmp.has_data = false;

    EXEC_RAISE(bq27520_read_flash_block(&tmp));
    if (!tmp.has_data) {
        mp_raise_ValueError(MP_ERROR_TEXT("Could not read data flash"));
        return mp_const_none;
    }

    tmp.data[10] = (mod_passport_fuelgauge_design_capacity >> 8) & 0x00FF;
    tmp.data[11] = (mod_passport_fuelgauge_design_capacity) & 0x00FF;
    EXEC_RAISE(bq27520_write_flash_block(&tmp));

    HAL_Delay(1200);

    // Registers Subclass
    tmp.class = 64;
    tmp.block = 0;
    memset(tmp.data, 0, sizeof(tmp.data));
    tmp.has_data = false;
    EXEC_RAISE(bq27520_read_flash_block(&tmp));
    if (!tmp.has_data) {
        mp_raise_ValueError(MP_ERROR_TEXT("Could not read data flash"));
        return mp_const_none;
    }

    tmp.data[0] = (CUSTOM_BQ27520_OPCONFIG >> 8) & 0x00FF;
    tmp.data[1] = (CUSTOM_BQ27520_OPCONFIG) & 0x00FF;
    EXEC_RAISE(bq27520_write_flash_block(&tmp));
#endif

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_configure_obj, mod_passport_fuelgauge_configure);

/// def bat_low_callback(self, bat_low_callback) -> None:
///     """
///     Register battery low callback on the external interrupt handler.
///
///     The callback runs in IRQ context.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_bat_low_callback(mp_obj_t bat_low_callback_obj) {
    extint_register((mp_obj_t)MICROPY_HW_BQ27520_BAT_LOW_PIN, GPIO_MODE_IT_RISING_FALLING, GPIO_NOPULL,
                    bat_low_callback_obj, true);
    extint_enable(MICROPY_HW_BQ27520_BAT_LOW_PIN->pin);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_fuelgauge_bat_low_callback_obj, mod_passport_fuelgauge_bat_low_callback);

/// def soc_int_callback(self, soc_int_callback) -> None:
///     """
///     Register SOC_INT interrupt callback on the driver interrupt handler.
///
///     The callback runs in IRQ context.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_soc_int_callback(mp_obj_t soc_int_callback_obj) {
    mod_passport_fuelgauge_user_soc_int_callback_obj = soc_int_callback_obj;
    bq27520_register_soc_int_cb(mod_passport_fuelgauge_soc_int_driver_cb);
    extint_enable(MICROPY_HW_BQ27520_SOC_INT_PIN->pin);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_fuelgauge_soc_int_callback_obj, mod_passport_fuelgauge_soc_int_callback);

/// def is_sealed() -> boolean:
///     """
///     Checks if the fuel gauge is sealed.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_is_sealed(void) {
    bool tmp = false;
    EXEC_RAISE(bq27520_is_sealed(&tmp));
    return tmp ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_is_sealed_obj, mod_passport_fuelgauge_is_sealed);

/// def seal() -> None:
///     """
///     Seal the fuel gauge.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_seal(void) {
    EXEC_RAISE(bq27520_seal());
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_seal_obj, mod_passport_fuelgauge_seal);

/// def read_volt() -> int:
///     """
///     Read a voltage from the bq27520 and return in a tuple because
///     we need the whole value and fraction (unable to return floats)
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_volt(void) {
    uint16_t volt = 0;
    EXEC_RAISE(bq27520_read_volt(&volt));
    return mp_obj_new_int_from_uint(volt);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_volt_obj, mod_passport_fuelgauge_read_volt);

/// def read_soc(self) -> int:
///     """
///     Get battery percentage 0-100 percent
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_soc(void) {
    uint16_t soc = 0;
    EXEC_RAISE(bq27520_read_soc(&soc));
    return mp_obj_new_int_from_uint(soc);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_soc_obj, mod_passport_fuelgauge_read_soc);

/// def read_reamining_capacity(self) -> int:
///     """
///     Get battery remaining capacity
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_remaining_capacity(void) {
    uint16_t remaining_capacity = 0;
    EXEC_RAISE(bq27520_read_capacity(BQ27520_CAPACITY_REMAINING, &remaining_capacity));
    return mp_obj_new_int_from_uint(remaining_capacity);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_remaining_capacity_obj,
                                 mod_passport_fuelgauge_read_remaining_capacity);

/// def read_full_charge_capacity(self) -> int:
///     """
///     Get battery full_charge capacity
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_full_charge_capacity(void) {
    uint16_t full_charge_capacity = 0;
    EXEC_RAISE(bq27520_read_capacity(BQ27520_CAPACITY_FULL_CHARGE, &full_charge_capacity));
    return mp_obj_new_int_from_uint(full_charge_capacity);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_full_charge_capacity_obj,
                                 mod_passport_fuelgauge_read_full_charge_capacity);

/// def read_temp(self) -> int:
///     """
///     Read temperature from the bq27520 and return it
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_temp(void) {
    uint16_t temp = 0;
    EXEC_RAISE(bq27520_read_temp(&temp));
    return mp_obj_new_int_from_uint(temp);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_temp_obj, mod_passport_fuelgauge_read_temp);

/// def read_time_to_empty(self) -> int:
///     """
///     Read time until empty (minutes) from the bq27520 and return it
///     """
STATIC mp_obj_t mod_passport_fuelgauge_read_time_to_empty(void) {
    return mp_obj_new_int_from_uint(0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_read_time_to_empty_obj,
                                 mod_passport_fuelgauge_read_time_to_empty);

/// def is_battery_detected() -> boolean:
///     """
///     Checks if the battery is connected to the fuel gauge.
///     """
STATIC mp_obj_t mod_passport_fuelgauge_is_battery_detected(void) {
    bool tmp = false;
    EXEC_RAISE(bq27520_is_battery_detected(&tmp));
    return tmp ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_fuelgauge_is_battery_detected_obj, mod_passport_fuelgauge_is_battery_detected);

/// SOC_INT IRQ callback. Calls the driver handler directly.
STATIC mp_obj_t mod_passport_fuelgauge_soc_int_irq_callback(mp_obj_t line) {
    bq27520_soc_int_isr();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_fuelgauge_soc_int_irq_callback_obj,
                                 mod_passport_fuelgauge_soc_int_irq_callback);

/// SOC_INT callback registered on the driver, it's called after the pulse width is completed. Then we call
/// the micropython handler here.
STATIC void mod_passport_fuelgauge_soc_int_driver_cb(uint32_t pulse_width) {
    if (mod_passport_fuelgauge_user_soc_int_callback_obj != mp_const_none) {
        mp_sched_lock();
        // When executing code within a handler we must lock the GC to prevent
        // any memory allocations.  We must also catch any exceptions.
        gc_lock();
        nlr_buf_t nlr;
        if (nlr_push(&nlr) == 0) {
            mp_call_function_1(mod_passport_fuelgauge_user_soc_int_callback_obj, mp_obj_new_int_from_uint(pulse_width));
            nlr_pop();
        } else {
            // Uncaught exception; disable the callback so it doesn't run again.
            mod_passport_fuelgauge_user_soc_int_callback_obj = mp_const_none;
            extint_disable(MICROPY_HW_BQ27520_SOC_INT_PIN->pin);
            mp_printf(MICROPY_ERROR_PRINTER, "uncaught exception in SOC_INT interrupt handler line\n");
            mp_obj_print_exception(&mp_plat_print, MP_OBJ_FROM_PTR(nlr.ret_val));
        }
        gc_unlock();
        mp_sched_unlock();
    }
}

STATIC const mp_rom_map_elem_t mod_passport_fuelgauge_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_passport_fuelgauge_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_probe), MP_ROM_PTR(&mod_passport_fuelgauge_probe_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_configured), MP_ROM_PTR(&mod_passport_fuelgauge_is_configured_obj)},
    {MP_ROM_QSTR(MP_QSTR_configure), MP_ROM_PTR(&mod_passport_fuelgauge_configure_obj)},
    {MP_ROM_QSTR(MP_QSTR_bat_low_callback), MP_ROM_PTR(&mod_passport_fuelgauge_bat_low_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_soc_int_callback), MP_ROM_PTR(&mod_passport_fuelgauge_soc_int_callback_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_sealed), MP_ROM_PTR(&mod_passport_fuelgauge_is_sealed_obj)},
    {MP_ROM_QSTR(MP_QSTR_seal), MP_ROM_PTR(&mod_passport_fuelgauge_seal_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_volt), MP_ROM_PTR(&mod_passport_fuelgauge_read_volt_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_soc), MP_ROM_PTR(&mod_passport_fuelgauge_read_soc_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_remaining_capacity), MP_ROM_PTR(&mod_passport_fuelgauge_read_remaining_capacity_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_full_charge_capacity), MP_ROM_PTR(&mod_passport_fuelgauge_read_full_charge_capacity_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_temp), MP_ROM_PTR(&mod_passport_fuelgauge_read_temp_obj)},
    {MP_ROM_QSTR(MP_QSTR_read_time_to_empty), MP_ROM_PTR(&mod_passport_fuelgauge_read_time_to_empty_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_battery_detected), MP_ROM_PTR(&mod_passport_fuelgauge_is_battery_detected_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_fuelgauge_globals, mod_passport_fuelgauge_globals_table);

STATIC const mp_obj_module_t mod_passport_fuelgauge_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_passport_fuelgauge_globals,
};
#endif  // HAS_FUEL_GAUGE