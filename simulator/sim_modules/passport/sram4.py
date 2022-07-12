# SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

MAX_QR_VERSION = 24


def _qr_get_module_size_for_version(version):
    return version * 4 + 17


def _qr_buffer_size_for_version(version):
    size = _qr_get_module_size_for_version(version)
    return ((size * size) + 7) // 8


def _alloc(ln):
    return bytearray(ln)


ext_settings_buf = _alloc(16 * 1024)
tmp_buf = _alloc(1024)
psbt_tmp256 = _alloc(256)
qrcode_buffer = _alloc(240 * 240)
qrcode_modules_buffer = _alloc(_qr_buffer_size_for_version(MAX_QR_VERSION))


def qrcode_buffer_clear():
    global qrcode_buffer
    qrcode_buffer[2 * 4:] = b'\x00' * (240 * 240)