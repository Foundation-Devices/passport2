# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# validate_psbt_task.py - Sign a PSBT that is in external SPI flash


async def validate_psbt_task(on_done, psbt_len):
    from errors import Error
    from exceptions import FraudulentChangeOutput, FatalPSBTIssue
    from psbt import psbtObject
    from public_constants import TXN_INPUT_OFFSET
    from sffile import SFFile
    import gc
    import history
    import progress

    error_msg = None
    error_code = None

    # Do the main validation
    psbt = None
    try:
        # Shares of the progress shown, from timings on the device: checking the
        # inputs' previous transactions and keys takes most of the time.
        progress.phase(0, 6)
        history.load()
        # Read TXN from SPI Flash (we put it there whether it came from a QR code or an SD card)
        with SFFile(TXN_INPUT_OFFSET, length=psbt_len) as fd:
            psbt = psbtObject.read_psbt(fd)

        gc.collect()
        progress.phase(6, 24)
        await psbt.validate()
        gc.collect()
        progress.phase(24, 84)
        psbt.consider_inputs()
        gc.collect()
        progress.phase(84, 85)
        psbt.consider_keys()
        gc.collect()
        progress.phase(85, 88)
        psbt.consider_timelocks()
        gc.collect()
        progress.phase(88, 100)
        psbt.consider_outputs()

        # All went well!
    except FraudulentChangeOutput as e:
        # print('validate_psbt_task 1')
        error_msg = e.args[0]
        error_code = Error.PSBT_FRAUDULENT_CHANGE_ERROR
    except FatalPSBTIssue as e:
        # print('validate_psbt_task 2')
        error_msg = e.args[0]
        error_code = Error.PSBT_FATAL_ERROR
    except MemoryError as e:
        # print('validate_psbt_task 3')
        error_msg = 'Transaction is too complex: {}'.format(e)
        error_code = Error.OUT_OF_MEMORY_ERROR
    except BaseException as e:
        # print('validate_psbt_task 4')
        error_msg = 'Invalid PSBT: {}'.format(e)
        error_code = Error.PSBT_FATAL_ERROR
    finally:
        # print('validate_psbt_task 5 - finally')
        if error_code is not None:
            del psbt
            psbt = None
        gc.collect()

        await on_done(psbt, error_msg, error_code)
