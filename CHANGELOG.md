<!--
SPDX-FileCopyrightText: 2023 Foundation Devices, Inc. <hello@foundationdevices.com>

SPDX-License-Identifier: GPL-3.0-or-later
-->

## Head
- Added changelog #581
- Cleared flash after signing transactions #345

## 2.0.5
- Fixed sign via microsd success page #545
- Fixed up/down keys on pin entry page #573
- Fixed UI memory leaks #572
- Fixed direction keys on pin entry page #567
- Carried over quirc library from Founder's Edition #558
- Used constants where possible #555
- Fixed Casa microsd export #534
- Carried over camera parameters from Founder's Edition #551
- Fixed os.sync not present in the simulator #546
- Fixed microsd error handling #543, #541, #526
- Added Keeper wallet integration #542
- Moved passphrase display to show seed words flow #536
- Reset extension settings and default search address upon erase #535
- Used 4:3 camera resolution #539
- Fixed mono colors for various features #538
- Improved Casa health check error handling #532
- Improved address verification animation #529
- Fixed special character UI memory leak #533
- Fixed mono QR scanning #530
- Reduced keypad cooldown to 50 ms #527
- Sped up address verification #437
- Improved mono color choice for security word box #531
- Revised pin entry page code #510
- Used root xfp as the backup file name #517, #523
- Updated mono icons #522
- Allowed users to change setup method #506
- Documented developer pubkey setup #515
- Fixed confirmation page when cancelling backup #512
- Made keypad match device version #521
- Added flash bootloader with secrets Just recipe #520
- Improved multisig import error handling #504
- Ensured extension accounts show the passphrase indicator #514
- Showed security words immediately after feature activation #503
- Looped through menu pages #513
- Prevented accidental double clicks #509
- Ported the current codebase to Passport Founder's Edition
- Made supply chain validation error more specific #505
- Fixed camera rotation on Founder's Edition #495
- Automatically generated required directories for the simulator #502
- Prevented security word indexing #157
- Pushed back auto shutdown while scanning QR codes #165
- Replaced keypad interrupts with polling
- Made camera widget size adaptable #492
