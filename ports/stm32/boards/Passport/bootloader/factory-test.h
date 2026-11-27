// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// factory-test.h - Code for testing Passport boards before final provisioning and lockdown.

// The factory test will execute code and place a result code in a specific memory address, along with
// a text error string if there was a failure.

// TheFactoryTestInfo struct is setup at the start of SRAM4 memory and is used to pass commands and arguments
// into the factory test firmware, as well as to pass responses back to the provisioning tool.  The latch
// system whose behavior is described below.
//
// The value in `latch` is initially be set to 0 indicating that no operation has been requested.
//
// To request a new test/function, the The provisioning tool can write a new operation number to the
// `pFactoryTestInfo->function`, optionally sets `param1` and `param2`, then sets `pFactoryTest->progress`
// to `FACTORY_TEST_COMMAND_READY`.
//
// The provisioning bootloader sits in a loop watching `pFactoryTestInfo->progress` until it changes to
// `FACTORY_TEST_COMMAND_READY`.  It then calls the correct `function` passing `param1` and `param2`.
//
// The provisioning tool will read the `FACTORY_TEST_PROGRESS_ADDR` once every 0.5 seconds to see if the operation is
// complete.  The provisioning bootloader will set `FACTORY_TEST_PROGRESS_ADDR` to `100` when the called function
// returns.  The called function itself may call `factory_test_set_progress(p)` to set an integer percentage complete
// from `0` to `100`, especially for long-running operations, so that the provisioning tool operator can see progress
// being made.
//
// The called function MUST call `factory_test_set_success()` or `factory_test_set_error(rc, msg)` before it returns.
//
//

#include <stdint.h>

#define SRAM4_START 0x38000800
#define FACTORY_TEST_MESSAGE_MAX_LEN 127
#define FACTORY_TEST_COMMAND_READY 0xFFFFFFFF

// Result codes
#define FACTORY_TEST_OK 0
#define FACTORY_TEST_ERROR_UNKNOWN_FUNCTION 1
#define FACTORY_TEST_PLEASE_CONFIRM 2

// Provisioning software writes a number here to indicate which test to run
typedef struct FactoryTestInfo {
    volatile uint32_t function;
    volatile uint32_t param1;  // Function parameter 1
    volatile uint32_t param2;  // Function parameter 2
    volatile uint32_t progress;
    volatile uint32_t result_code;
    volatile char     message[FACTORY_TEST_MESSAGE_MAX_LEN + 1];
} FactoryTestInfo;

// Utility functions for setting success/error/progress in the tests
void factory_test_set_result_success();
void factory_test_set_result_ask_confirmation();
void factory_test_set_result_error(uint32_t result_code, char* message);
void factory_test_set_progress(uint32_t percent_complete);

// The available test functions

#define FACTORY_TEST_FUNC_LCD 1
#define FACTORY_TEST_FUNC_CAMERA 2
#define FACTORY_TEST_FUNC_EEPROM 3
#define FACTORY_TEST_FUNC_KEYPAD 4
#define FACTORY_TEST_FUNC_SD_CARD 5
#define FACTORY_TEST_FUNC_FUEL_GAUGE 6
#define FACTORY_TEST_FUNC_EXTERNAL_FLASH 7
#define FACTORY_TEST_FUNC_SECURE_ELEMENT 8
#define FACTORY_TEST_FUNC_AVALANCHE_NOISE_SOURCE 9
#define FACTORY_TEST_FUNC_PROGRAM_SPI_FLASH 10
#define FACTORY_TEST_MAX_FUNCTION_NUM 10

void factory_test_loop();
void factory_test_lcd(uint32_t param1, uint32_t param2);
void factory_test_camera(uint32_t param1, uint32_t param2);
void factory_test_eeprom(uint32_t param1, uint32_t param2);
void factory_test_keypad(uint32_t param1, uint32_t param2);
void factory_test_sd_card(uint32_t param1, uint32_t param2);
void factory_test_fuel_gauge(uint32_t param1, uint32_t param2);
void factory_test_external_flash(uint32_t param1, uint32_t param2);
void factory_test_secure_element(uint32_t param1, uint32_t param2);
void factory_test_avalanche_noise_source(uint32_t param1, uint32_t param2);
