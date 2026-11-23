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
    # Only a successful Restore read hands the plaintext to the caller. Every other way out,
    # including an exception raised by the checks below, clears it in the finally.
    caller_owns_contents = False

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
                        return None, Error.INVALID_BACKUP_CODE

                    # Restore refuses a backup that doesn't start with this exact line, so Verify
                    # checks it too. The contents are a bytearray, which has no startswith() in
                    # MicroPython.
                    header = BACKUP_FILE_HEADER.encode()
                    if contents[:len(header)] != header:
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

        if validate_only:
            return None, None

        caller_owns_contents = True
        return contents, None
    except CardMissingError:
        return None, Error.MICROSD_CARD_MISSING
    except MemoryError:
        return None, Error.OUT_OF_MEMORY_ERROR
    except OSError:
        return None, Error.FILE_READ_ERROR
    except Exception:
        return None, Error.FILE_READ_ERROR
    finally:
        if not caller_owns_contents:
            _clear_contents(contents)


def verify_backup_file(decryption_password, backup_file_path):
    # This confirms the supplied code or password decrypts the archive, the plaintext CRC matches
    # and the Passport backup header is valid. Restore still checks the contents afterwards,
    # including that a valid raw_secret is present, so it can refuse a backup that passes here.
    # Decryption necessarily materializes plaintext, so it is cleared before returning.
    _contents, error = read_backup_file(
        decryption_password, backup_file_path, validate_only=True)
    return error
