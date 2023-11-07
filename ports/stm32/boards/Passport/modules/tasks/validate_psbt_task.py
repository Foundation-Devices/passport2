# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# validate_psbt_task.py - Sign a PSBT that is in external SPI flash
from errors import Error
from exceptions import FraudulentChangeOutput, FatalPSBTIssue
from public_constants import TXN_INPUT_OFFSET
from sffile import SFFile
import gc
from utils import mem_info


async def validate_psbt_task(on_done, psbt_len):
    mem_info('validate_psbt_task before import')

    from psbt import psbtObject

    mem_info('validate_psbt_task after import')

    error_msg = None
    error_code = None

    # Do the main validation
    psbt = None
    try:
        # Read TXN from SPI Flash (we put it there whether it came from a QR code or an SD card)
        with SFFile(TXN_INPUT_OFFSET, length=psbt_len) as fd:
            mem_info('with sffile')
            psbt = psbtObject.read_psbt(fd)

        mem_info('validate_psbt_task after read')
        await psbt.validate()
        mem_info('validate_psbt_task after validate')
        psbt.consider_inputs()
        mem_info('validate_psbt_task after consider_inputs')
        psbt.consider_keys()
        mem_info('validate_psbt_task after consider_keys')
        psbt.consider_outputs()
        mem_info('validate_psbt_task after consider_outputs')

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
