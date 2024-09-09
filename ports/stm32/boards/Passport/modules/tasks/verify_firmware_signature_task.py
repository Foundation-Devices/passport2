# Task to verify the signatures of a firmware update before copying to
# SPI flash.
#
# SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later

import passport
import trezorcrypto
import foundation
from uasyncio import sleep_ms
from ubinascii import hexlify as b2a_hex
from constants import FW_HEADER_SIZE, FW_HEADER_INFORMATION_SIZE
from files import CardSlot, CardMissingError
from errors import Error


async def verify_firmware_signature_task(file_path, size, on_progress, on_done):
    header = None
    s = trezorcrypto.sha256()

    try:
        with CardSlot() as card:
            with open(file_path, 'rb') as fp:
                # This is assumed to have been validated before, TOCTOU
                # attacks are not an issue here since if the information data
                # changes so does the validation hash making the signature
                # verification to fail.
                header = fp.read(FW_HEADER_SIZE)
                s.update(header[:FW_HEADER_INFORMATION_SIZE])

                buf = bytearray(1024)
                pos = FW_HEADER_SIZE
                update_display = 0
                while pos < size:
                    # Update every 50 reads.
                    if update_display % 50 == 0:
                        percent = int((pos / size) * 100)
                        on_progress(percent)

                        # Allow UI to update progress.
                        await sleep_ms(1)

                    here = fp.readinto(buf)
                    s.update(buf[:here])
                    pos += here

                    update_display += 1
    except CardMissingError:
        await on_done(Error.MICROSD_CARD_MISSING, None)
        return
    except Exception as e:
        error_message = "Firmware update error: {}, Info: {}".format(e.__class__.__name__,
                                                                     e.args[0] if len(e.args) == 1 else e.args)
        await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
        return

    single_sha = s.digest()
    double_sha = bytearray(32)
    foundation.sha256(single_sha, double_sha)

    try:
        passport.verify_update_signatures(header, double_sha)
    except passport.InvalidFirmwareUpdate as e:
        await on_done(Error.FIRMWARE_UPDATE_FAILED, "Invalid firmware signatures")
        return
    except Exception as e:
        error_message = "Firmware update error: {}, Info: {}".format(e.__class__.__name__,
                                                                     e.args[0] if len(e.args) == 1 else e.args)
        await on_done(Error.FIRMWARE_UPDATE_FAILED, error_message)
        return

    await on_done(None, None)
