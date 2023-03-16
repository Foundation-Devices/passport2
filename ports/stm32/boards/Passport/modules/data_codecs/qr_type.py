# SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# qr_type.py
#
# QR types
#


class QRType:
    QR = 0               # Standard QR code with no additional encoding
    UR1 = 1              # UR 1.0 pre-standard from Blockchain Commons
    UR2 = 2              # UR 2.0 standard from Blockchain Commons
    COMPACT_SEED_QR = 3  # Compact SeedQR
    SEED_QR = 4          # SeedQR
