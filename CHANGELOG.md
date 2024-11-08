<!--
SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>

SPDX-License-Identifier: GPL-3.0-or-later
-->

## Head
- Improved self-send transaction information formatting (PASS1-638)
- Added the key manager extension, compatible with BIP85 and Nostr (PASS1-24)

## 2.0.7
- Perform more accurate calculation of scan progress. (PASS1-553)
- Report to the user when the data contained in a QR code is not a PSBT. (PASS1-553)
- Improved the QR code scan error reporting. (PASS1-553)
- Removed support for [UR1] animated QR codes (PASS1-620)
- Improved Founder's Edition screen performance (PASS1-576)
- Automatically generate hash files using "just hash" (PASS1-605)
- Added a success screen after multisig imports (PASS1-593)
- Improved file display error handling (PASS1-584)
- Added option to delete files from the SD card (PASS1-618)
- Added Casa health check via SD card (PASS1-595)
- Added multisig config export via QR and SD card (PASS1-631)
- Fixed multisig config descriptions (PASS1-643)
- Improved the UR animated QR codes encoder and decoder to allow signing
bigger transactions. (SFT-1063)
- Fix camera color issue. (SFT-1428)

[UR1]: https://github.com/CoboVault/Research/blob/master/papers/bcr-0005-ur.md

## 2.0.6
- Fixed alphanumeric pin entry timing (PASS1-655)

## 2.0.5
- Ensured "New Account" UI returns to the "More" menu (PASS1-582)
- Added changelog (PASS1-581)
- Reverted some changes to multisig imports (PASS1-504)
- Reduced keypad double click cooldown to 20 ms (PASS1-509)
- Reverted multisig import to only check against the current XFP (PASS1-587)
- Reverted backup code page cursor color to previous look (PASS1-591)
- Limited number of files on the file picker page (PASS1-584)
- Fixed passphrase and account header text color (PASS1-582)
- Raised passphrase character limit to 1000 (PASS1-519)
- Fixed sign via microsd success page (PASS1-545)
- Fixed up/down keys on pin entry page (PASS1-573)
- Fixed UI memory leaks (PASS1-572)
- Fixed direction keys on pin entry page (PASS1-567)
- Carried over quirc library from Founder's Edition (PASS1-558)
- Used constants where possible (PASS1-555)
- Fixed Casa microsd export (PASS1-534)
- Carried over camera parameters from Founder's Edition (PASS1-551)
- Fixed os.sync not present in the simulator (PASS1-546)
- Fixed microsd error handling (PASS1-543, PASS1-541, PASS1-526)
- Added Keeper wallet integration (PASS1-542)
- Moved passphrase display to show seed words flow (PASS1-536)
- Reset extension settings and default search address upon erase (PASS1-535)
- Used 4:3 camera resolution (PASS1-539)
- Fixed mono colors for various features (PASS1-538)
- Improved Casa health check error handling (PASS1-532)
- Improved address verification animation (PASS1-529)
- Fixed special character UI memory leak (PASS1-533)
- Fixed mono QR scanning (PASS1-530)
- Reduced keypad cooldown to 50 ms (PASS1-527)
- Sped up address verification (PASS1-437)
- Improved mono color choice for security word box (PASS1-531)
- Revised pin entry page code (PASS1-510)
- Used root xfp as the backup file name (PASS1-517, PASS1-523)
- Updated mono icons (PASS1-522)
- Allowed users to change setup method (PASS1-506)
- Documented developer pubkey setup (PASS1-515)
- Fixed confirmation page when cancelling backup (PASS1-512)
- Made keypad match device version (PASS1-521)
- Added flash bootloader with secrets Just recipe (PASS1-520)
- Improved multisig import error handling (PASS1-504)
- Ensured extension accounts show the passphrase indicator (PASS1-514)
- Showed security words immediately after feature activation (PASS1-503)
- Looped through menu pages (PASS1-513)
- Prevented accidental double clicks (PASS1-509)
- Ported the current codebase to Passport Founder's Edition
- Made supply chain validation error more specific (PASS1-505)
- Fixed camera rotation on Founder's Edition (PASS1-495)
- Automatically generated required directories for the simulator (PASS1-502)
- Prevented security word indexing (PASS1-157)
- Pushed back auto shutdown while scanning QR codes (PASS1-165)
- Replaced keypad interrupts with polling
- Made camera widget size adaptable (PASS1-492)
