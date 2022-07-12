<!--
SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Development

This document describes how to develop for Passport.

## Operating System
While Passport may compile on other Linux distributions, the instructions below are based on **Ubuntu 18.04**, which is also what is used for official Passport builds.

## Installation

### Get the Source Code
The instructions below assume you are installing into your home folder at `~/passport-firmware`.  You can choose
to install to a different folder, and just update command paths appropriately.

    cd ~/
    git clone git@github.com:Foundation-Devices/passport-firmware.git

### Install Dependencies
Several tools are required for building and debugging Passport.

#### Cross-Compiler Toolchain
    sudo apt install gcc-arm-none-eabi
    cd ~/passport-firmware
    make -C mpy-cross

#### Autotools and USB

    sudo apt install autotools-dev automake libusb-1.0.0-dev libtool python3-virtualenv libsdl2-dev pkg-config curl

#### OpenOCD - On-Chip Debugger
    cd ~/
    git clone https://github.com/ntfreak/openocd.git
    cd ~/openocd/
    ./bootstrap
    ./configure --enable-stlink
    make
    sudo make install

#### RShell - Micropython Shell and REPL
    cd ~/
    git clone https://github.com/dhylands/rshell
    sudo apt install python3-pip
    sudo pip3 install rshell                                  # (this should install rshell in /usr/local/)

### Using Justfile commands
To use Just for running commands, first follow the instructions here: https://github.com/casey/just#installation to install Just. Note that `Pillow` must be updated to `8.3.1` for all commands to work properly.

Once Just has been installed, the developer can use `just` commands to perform actions such as building, flashing, resetting and even taking screenshots of the displays screen.

Note that all `just` commands must be run from `ports/stm32/` directory.

Here are some of the most common `just` commands and their usages:

    just flash {version} - Builds if necessary, signs with a user key and then flashes the device with the firmware binary created under `build-Passport/`
    just reset - Resets the device
    just screenshot {filename} - Screenshots the device and saves to the desired filename

See the `Justfile` included in our source for the full list of `just` commands.

## Building
### Open Shell Windows/Tabs
You will need several shell windows or tabs open to interact with the various tools.

### Build Window

#### Building the Simulators
TBD: 
    virtualenv -p python3 ENV
    source ENV/bin/activate
    pip install -r requirements.txt


#### Building the Main Firwmare
In one shell, make sure that you `cd` to the root `stm32` source folder, e.g., `cd ~/passport-firmware/ports/stm32`:

    make BOARD=Passport

To include debug symbols for use in `ddd`, run the following:

    make BOARD=Passport DEBUG=1

You should see it building various `.c` files and freezing `.py` files.  Once complete, the final output should look similar to the following:

    LINK build-Passport/firmware.elf
    text	   data	    bss	    dec	    hex	filename
    475304	    792	  57600	 533696	  824c0	build-Passport/firmware.elf
    GEN build-Passport/firmware.dfu
    GEN build-Passport/firmware.hex

If you are using `just` commands, then building the firmware can be done by running the following command:

    just build

#### Code Signing
In order to load the files onto the device, they need to first be signed by two separate keys.
The `cosign` program performs this task, and it needs to be called twice with two separate
private keys.

First, you need to build the `cosign` tool and copy it somewhere in your `PATH`:

    sudo apt-get install libssl-dev
    cd ports/stm32/boards/Passport/tools/cosign
    make
    cp x86/release/cosign ~/.local/bin   # You can run `echo $PATH` to see the list of possible places you can put this file


Next you need to sign the firmware twice.  The `cosign` tool appends `-signed` to the end of the main filename each time it signs.
Assuming you are still in the `ports/stm32` folder run the following:

    # TODO: Update command arguments once final signing flow is in place
    cosign -f build-Passport/firmware.bin -k 1 -v 0.9
    cosign -f build-Passport/firmware-signed.bin -k 2

You can also dump the contents of the firmware header with the following command:

    cosign -f build-Passport/firmware-signed-signed.bin -x

If you are using `just` commands, then signing the firmware can be done by running the following command with the desired version:

    just sign 1.0.7

It will build the firmware first if necessary.

#### Building the Bootloader
To build the bootloader do the following:

    cd ports/stm32/boards/Passport/bootloader folder
    make

If you're using dev. board and wish to swap out the secure element chip, you can define
`USE_DEVBOARD_SE_SOCKET` for the bootloader to use the chip from dev. board socket.

### OpenOCD Server Window
OpenOCD server provides a socket on `localhost:4444` that you can connect to and issue commands.  This server acts as an intermediary between that socket and the board connected over JTAG.

Once the OpenOCD server is running, you can pretty much ignore this window.  You will interact with the OpenOCD client window (see below).  Open a second shell and run the following:

    /usr/local/bin/openocd -f stlink.cfg -c "adapter speed 1000; transport select hla_swd" -f stm32h7x.cfg

You should see output similar to the following:

    Open On-Chip Debugger 0.10.0+dev-01383-gd46f28c2e-dirty (2020-08-24-08:31)
    Licensed under GNU GPL v2
    For bug reports, read
        http://openocd.org/doc/doxygen/bugs.html
    hla_swd
    Info : The selected transport took over low-level target control. The results might differ compared to plain JTAG/SWD
    Info : Listening on port 6666 for tcl connections
    Info : Listening on port 4444 for telnet connections
    Info : clock speed 1800 kHz
    Info : STLINK V2J29S7 (API v2) VID:PID 0483:3748
    Info : Target voltage: 2.975559
    Info : stm32h7x.cpu0: hardware has 8 breakpoints, 4 watchpoints
    Info : starting gdb server for stm32h7x.cpu0 on 3333
    Info : Listening on port 3333 for gdb connections

### OpenOCD Client Window (aka `telnet` Window)
We use `telnet` to connect to the OpenOCD Server.  Open a third shell and run the following:

    telnet localhost 4444

From here can connect over JTAG and run a range of commands (see the help for OpenOCD for details):

Whenever you change any code in the `bootloader` folder or in the `common` folder, you will need to rebuild the bootloader (see above), and then flash it to the device with the following sequence in OpenOCD:

    reset halt
    flash write_image erase boards/Passport/bootloader/arm/release/bootloader.bin 0x8000000
    reset

### TBD: Add docs on appending secrets to the end of the bootloader.bin file during development.

The following command sequence is one you will run repeatedly (i.e., after each build):

    reset halt
    flash write_image erase build-Passport/firmware-signed-signed.bin 0x8020000
    reset

These commands do the following:

- Stop execution of code on the MCU
- Write the firmware to flash at address 0x8000000
- Reset the MCU and start executing code at address 0x8000000

If you are using `just` commands, ocd and telnet steps are not required and instead, flashing the firmware can be done using the following command with the desired version number:

    just flash 1.0.7

It will build and sign the firmware first if necessary.

### RShell Window
We use `rshell` to connect to the MicroPython device over USB serial.  Open another shell and run:

    sudo rshell -p /dev/ttyUSB0

This gives us an interactive shell where we can do things like inspect the flash file system, or run a REPL:

- `ls -la /flash` - Get a listing of the files in `/flash` on the device
- `cp local_folder/my_math.py /flash` - Copy a local file into `/flash`
- `repl` - Open a MicroPython REPL.  If there are any files in `/flash`, you can import them.  For example:

```
import my_math
my_math.add(1, 2)
```

### Debugging with DDD
To debug the firmware, open a new shell window or tab and run the following command from the `passport/ports/stm32` folder:

    ddd --debugger gdb-multiarch build-Passport/firmware.elf &

To debug the bootloader, open a new shell window or tab and run the following command from the `passport/ports/stm32/boards/Passport/bootloader` folder:

    ddd --debugger gdb-multiarch bootloader.elf &

Go to the `telnet` session with OpenOCD and run the following to prepare to connect DDD:

    reset halt

Next, connect DDD to the OpenOCD GDB server with:

    target remote localhost:3333

From here you can run normal GDB commands like:

    b stm32_main          # Stop at stm32_main, which is MicroPython's entry point
    list main.c           # Show the main.c file at line 1
    c                     # continue
    n                     # step over
    s                     # step into
