<!--
SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>

SPDX-License-Identifier: GPL-3.0-or-later
-->

# Passport Wallet Firmware

Passport is an ultra-secure, open source hardware wallet for Bitcoin that offers excellent usability and a great design.

Get yours at [foundationdevices.com](https://foundationdevices.com) and [follow @FOUNDATIONdvcs on Twitter](https://twitter.com/FOUNDATIONdvcs) to keep up with the latest updates and security alerts.

<img src="https://user-images.githubusercontent.com/62639971/100824536-2ed61a00-340b-11eb-9283-46174164bc84.jpg" width="800"/>

## Project Structure

The source code is organized according to the standard MicroPython project structure.

The source is, broadly speaking, split into two parts:

-   **Bootloader.** This is typically flashed into the device permanently at the factory, although we may release developer versions of Passport that allow users to flash their own bootloader.

-   **Main Firmware.** This is the main, updatable software running on Passport that provides the UI and wallet features.

Code specific to Passport is included in the following folders:

-   [`ports/stm32`](ports/stm32) Low-level platform configuration for MicroPython.
-   [`ports/stm32/boards/Passport`](ports/stm32/boards/Passport) C files that implement some device drivers and code that was 5-10 times faster in C than in Python.
-   [`bootloader`](ports/stm32/boards/Passport/bootloader) C-based code that handles secure element initialization, firmware validation and updates, and system startup.
-   [`common`](ports/stm32/boards/Passport/common) Common C code shared between the bootloader and the main firmware.
-   [`graphics`](ports/stm32/boards/Passport/graphics) Images and a build script that converts the images to Python data for easier loading.
-   [`modules`](ports/stm32/boards/Passport/modules) The MicroPython code that implements the user interface and menu actions.
-   [`trezor-firmware`](extmod/trezor-firmware) Contains a copy of the Trezor source code in order to use Trezor's crypto library. We will likely make this into a git submodule soon to make it even easier to keep the library up to date.
-   [`tools/cosign`](ports/stm32/boards/Passport/tools/cosign) - A C-based utility that provides the code signing that keeps Passport's firmware safe.
-   [`utils`](ports/stm32/boards/Passport/utils) Some CLI utilities used to generate BIP39 data for seed word lookup.

## Development

Please see [`DEVELOPMENT.md`](DEVELOPMENT.md) for information on developing for Passport.

## Verifying Firmware SHA Sums

To make building and verifying the firmware a simple process, there is a Dockerfile in the project that builds an image to be used to build the firmware. Using [`just`](https://github.com/casey/just), the following command can be used to verify the reproducability of the firmware. Make sure to substitute `<the sha sum>` for the SHA string to verify.

```shell
just verify-sha <the-sha-sum>
```

## Open Source Components

Passport's firmware incorporates open-source software from several third-party projects, as well as other first-party work we open-sourced.

-   [MicroPython](https://github.com/micropython/micropython) - This forms the core foundation on which Passport is built.

-   [Coldcard Firmware](https://github.com/Coldcard/firmware) - Passport's security model has a lot in common with Coldcard, and the Passport firmware was originally based directly on the ColdCard repository. As development progressed, however, we chose to follow MicroPython best practices and start with a fresh MicroPython repository. We've ported numerous files from Coldcard as needed, and we thank them for their great contribution to open source.

-   [Trezor Firmware](https://github.com/trezor/trezor-firmware) - Trezor has kindly open-sourced a highly-optimized library of crypto algorithms. Rather than modify the Trezor code, we decided to include the original source. This will make it easier to incorporate future improvements and fixes from Trezor and their contributors. We may convert this to a git submodule in the future.

-   [Quirc](https://github.com/dlbeer/quirc) - Quirc is a QR decoding library that offers an embedded-friendly interface to process images from a camera for QR codes. This library has proven to be fast and reliable in Passport. We made some changes and contributed back to Quirc (pull request pending).

-   [QRCode](https://github.com/ricmoo/QRCode) - QRCode is a QR code creator library that takes a string or data and encode it to a QR code which can then be displayed on screen, saved to file, etc. This library has a simple clean interface and was easy to integrate.

-   [Foundation UR Python 2.0](https://github.com/Foundation-Devices/foundation-ur-py) - This is our Python port of the UR 2.0 standard from the wonderful Blockchain Commons. It provides the ability to encode/decode multi-part animated QR codes that represent data which is too large to fit in a single QR code. This is the new standard air-gapped wallets are expected to adopt moving forward.

-   Foundation UR Python 1.0 (Coming Soon) - This is our Python port of the UR 1.0 standard from BlockChain Commons. It has the same goals as UR 2.0, but was more of an early experiment. Foundation Devices ported this to Python to be compatible with air-gapped software wallets like BlueWallet and Specter.

## Security Vulnerability Disclosure
Please report suspected security vulnerabilities in private to security@foundationdevices.com. Please do NOT create publicly viewable issues for suspected security vulnerabilities.

## Licensing

All licenses used in Passport are [reuse](https://reuse.software/) friendly, and the license for each component is marked separately in the header files where appropriate or in a `.reuse/dep5` file otherwise. See the `LICENSES` folder and the
`ports/stm32/boards/Passport/LICENSES` folders for details on each license file.

In summary, Passport makes use of the following licenses.

- Apache License, Version 2.0
- FreeBSD License (2-clause BSD License)
- FreeBSD (2-clause BSD) Plus Patent License
- Modified BSD License (3-clause BSD License)
- GNU General Public License v3.0 (GPLv3)
- GNU General Public License v3.0 (GPLv3) or later
- ISC License (OpenBSD)
- MIT License
- The Unlicense

**Due to the inclusion of GPLv3 code, Passport Firmware should be treated in a copyleft manner.**
