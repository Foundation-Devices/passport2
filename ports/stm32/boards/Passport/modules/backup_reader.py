# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# Read and validate encrypted Passport backup files without changing device state.

import compat7z

from constants import BACKUP_FILE_HEADER, MAX_BACKUP_FILE_SIZE
from errors import Error
from files import CardMissingError, CardSlot


def _clear_contents(contents):
    if contents is not None:
        for index in range(len(contents)):
            contents[index] = 0


def read_backup_file(decryption_password, backup_file_path, validate_only=False):
    contents = None

    try:
        with CardSlot():
            fd = open(backup_file_path, 'rb')

            try:
                try:
                    compat7z.check_file_headers(fd)
                except MemoryError:
                    return None, Error.OUT_OF_MEMORY_ERROR
                except OSError:
                    return None, Error.FILE_READ_ERROR
                except Exception:
                    return None, Error.INVALID_BACKUP_FILE_HEADER

                try:
                    zz = compat7z.Builder()
                    _fname, contents = zz.read_file(
                        fd,
                        decryption_password,
                        MAX_BACKUP_FILE_SIZE,
                        progress_fcn=None)

                    # Match Restore's existing plaintext sanity check.
                    if contents[0:1] != b'#' or contents[-1:] != b'\n':
                        _clear_contents(contents)
                        return None, Error.INVALID_BACKUP_CODE

                    # Every backup Passport has written starts with this exact line. Checking it
                    # here means Verify passes exactly what Restore accepts. The contents are a
                    # bytearray, which has no startswith() in MicroPython.
                    header = BACKUP_FILE_HEADER.encode()
                    if contents[:len(header)] != header:
                        _clear_contents(contents)
                        return None, Error.CORRUPT_BACKUP_FILE
                except MemoryError:
                    return None, Error.OUT_OF_MEMORY_ERROR
                except OSError:
                    return None, Error.FILE_READ_ERROR
                except Exception:
                    # The plaintext CRC deliberately does not distinguish a
                    # wrong code from damaged encrypted contents.
                    return None, Error.INVALID_BACKUP_CODE
            finally:
                fd.close()
    except CardMissingError:
        return None, Error.MICROSD_CARD_MISSING
    except MemoryError:
        _clear_contents(contents)
        return None, Error.OUT_OF_MEMORY_ERROR
    except OSError:
        _clear_contents(contents)
        return None, Error.FILE_READ_ERROR
    except Exception:
        _clear_contents(contents)
        return None, Error.FILE_READ_ERROR

    if validate_only:
        _clear_contents(contents)
        return None, None

    return contents, None


def verify_backup_file(decryption_password, backup_file_path):
    # Decryption necessarily materializes plaintext. Keep it inside this
    # validation boundary and clear the mutable buffer before returning.
    _contents, error = read_backup_file(
        decryption_password, backup_file_path, validate_only=True)
    return error
