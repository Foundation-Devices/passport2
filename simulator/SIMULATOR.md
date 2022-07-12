<!--
SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Passport Simulator

This document describes the architecture and operation of the Passport Simulator.

# Architecture
The simulator is divided into two major pieces:

1. MicroPython Unix Runtime
2. Simulator Front-End

The backend of the simulator is the standard MicroPython runtime with the Passport application running on it.  There are certain files that access hardware which are replaced with simulator equivalents:

* **Keypad** - The host computer's keystrokes are converted into equivalent keypresses added into the keypad queue of the Runtime.  There is a Unix pipe that sends the keystroke messages from the Simulator to the Runtime.

* **Camera** - Normally, the actual hardware camera would fill in the bytes of an on-device camera buffer in RAM.  In the Simulator, your webcam's color image is cropped to the center to match the hardware image size, and then the image bytes are sent over a Unix pipe to the Runtime and copied into the same buffer that the real camera would use.

* **Display** - The actual Passport hardware has a framebuffer the UI code renders into when updating the display.  Since the Unix Runtime does not have a display, it instead sends the scren image bytes to the Simulator over a Unix pipe.  These bytes are then passed to SDL to render the screen display on your computer.

* **microSD Card** - Instead of reading/writing files to the microSD card on the actual Passport hardware, the Unix Runtime reads/writes files to the `./simulator/work/microsd` folder.

* **Secure Element** - The actual Passport hardware has an ATECC608A/B chip, but on the Unix Runtime, we replace that with a simple module that implements similar features.  It is NOT secure at all and the functionality this module provides to the Unix Runtime is limited.

* **SPI Flash** - The Simulator provides a memory buffer to simulate SPI flash.

* **Red/Blue LEDs** - The Secure Element can turn on either the blue or red LED.  The simulator needs to be notified when the status of the LEDs changes.  This is done through another Unix pipe.

* **User Settings Flash** - Save/load settings values to/from a JSON file instead of to flash.

* **SRAM4** - Allocate blocks of PC RAM that are normally stored in an alternate RAM region in the actgual Passport hardware.

* **Version Info** - MicroPython normally provides several functions and values here.

More details on each of these is provided below.

# Command Line Options

***TBD***
- Skip login
- Mono/color
- Replace a specific version of settings.json with the given file and then start
- Jump to a specific screen?

# Simulator Code Structure
The `simulator` folder in the root of the repo contains the code to build and run the simulator.  The following locations are important:

* `simulator/simulator.py` - The main simulator Python executable.

* `simulator/sim_modules` - The Python classes that replace the functionality of the `*/c` files in the previous line.

* `simulator/work/settings.json` - A JSON file with the user settings values and the secure element state (all unencrypted).

* `simulator/work/micosd` - The file system that the simulator will see when the user triggers an action that reads/writes the microSD card slot.  You can find `error.log` files here too.

* `ports/unix` - The Unix port of MicroPython

* `ports/stm32/boards/Passport/modules` - The main Passport application code.

* `ports/stm32/boards/Passport/*.c` - The C files which are hardware-specific.  These are NOT loaded in the simulator.

# Importing Modules
The `simulator.py` code opens several pipes and passes the file handles of these, along with other values, as arguments to the Unix port of MicroPython.  In particular, it tells the MicroPython to launch `sim_start.py`, which is just a shim to load `modules/main.py`.

In order to find `main.py`, the simulator also sets `MICROPYPATH` in the shell environment to `:{cwd}./sim_modules:{cwd}/../ports/stm32/boards/Passport/modules`.  This tells MicroPython where to look when importing Python modules.  Note that the order here is very important.  Any classes in the `sim_modules` folder will take precedence over classes with the same name from the `Passport/modules` folder.  This allows the simulator to load simulated versions of modules that are not supported in the Unix port of the MicroPython/Passport code.

For example, you can find the `turbo()` function defined in the System class in `Passport/modfoundation.c`, but that is hardware-specific code and is not compatible with the simulator.  Instead, the file `sim_modules/passport/__init__.py` contains a definition of the System class which defines a `turbo()` function.


# Single Binary
For now, the code for Gen 1 and Gen 1.2 will compile into a single firmware binary.  This means that the Gen 1 firmware will contain color bitmaps and possibly more details fonts which it cannot use.  Similarly, when running on a Gen 1.2 device, there will be monochrome images and fonts that are not used.

We will need to monitor this during development to ensure that we do not exceed about 1.7MB in size, as that is all the space we have to load a firmware update into external SPI flash.
