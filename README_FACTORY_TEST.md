# Factory Test Mode for Passport

## Building Factory Test Bootloader

To build the bootloader with factory test functionality enabled:

```bash
# For mono screen
just ports/stm32/boards/Passport/bootloader/build mono release factory_test

# For color screen  
just ports/stm32/boards/Passport/bootloader/build color release factory_test
```

## Flashing Factory Test Bootloader

```bash
# Flash the factory test bootloader
just ports/stm32/boards/Passport/bootloader/flash mono release factory_test
```

## Using Factory Test Mode

The factory test bootloader provides a communication interface through SRAM4 memory at address `0x38000800`. The provisioning tool can write commands to this memory location to trigger various tests.

### Available Factory Tests

1. **LCD Test** (Function 1)
2. **Camera Test** (Function 2) 
3. **EEPROM Test** (Function 3)
4. **Keypad Test** (Function 4) ← This is what you want
5. **SD Card Test** (Function 5)
6. **Fuel Gauge Test** (Function 6)
7. **External Flash Test** (Function 7)
8. **Secure Element Test** (Function 8)
9. **Avalanche Noise Source Test** (Function 9)

### Keypad Test Details

The keypad test (Function 4) performs the following:
- Initializes the keypad controller (ADP-5587)
- Reads the number of keys in the queue
- Verifies the keypad is responding correctly

### Memory Interface

The factory test uses a shared memory structure at `0x38000800`:

```c
typedef struct FactoryTestInfo {
    volatile uint32_t function;     // Test function number (1-9)
    volatile uint32_t param1;       // Function parameter 1
    volatile uint32_t param2;       // Function parameter 2  
    volatile uint32_t progress;     // Progress indicator
    volatile uint32_t result_code;  // Result code
    volatile char message[128];     // Result message
} FactoryTestInfo;
```

### Running Keypad Test

To run the keypad test:

1. Set `function = 4` (FACTORY_TEST_FUNC_KEYPAD)
2. Set `progress = 0xFFFFFFFF` (FACTORY_TEST_COMMAND_READY)
3. Wait for `progress` to change to 100 (test complete)
4. Check `result_code` for success (0) or error

The test will return:
- **Success (0)**: "OK" - Keypad is working
- **Error (111)**: Various error messages like "Can't init keypad" or "Can't read number of keys"
