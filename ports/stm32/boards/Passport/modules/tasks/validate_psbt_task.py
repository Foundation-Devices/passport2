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


async def validate_psbt_task(on_done, on_event, psbt_len):
    from errors import Error
    from exceptions import FraudulentChangeOutput, FatalPSBTIssue
    from foundation import psbt
    from public_constants import TXN_INPUT_OFFSET
    from sffile import SFFile
    import chains
    import stash
    import gc

    error_msg = None
    error_code = None

    # Do the main validation
    details = None
    try:
        print('offset={} len={}'.format(TXN_INPUT_OFFSET, psbt_len))

        chain = chains.current_chain()
        is_testnet = chain.ctype == 'TBTC'

        with stash.SensitiveValues() as sv:
            xpriv = psbt.Xpriv(chain_code=sv.node.chain_code(),
                               private_key=sv.node.private_key())
            details = psbt.validate(TXN_INPUT_OFFSET, psbt_len, is_testnet, xpriv, on_event)
        # All went well!
    except psbt.InvalidPSBTError as e:
        # print('validate_psbt_task 2')
        error_msg = e.args[0]
        error_code = Error.PSBT_FATAL_ERROR
    except psbt.FraudulentPSBTError as e:
        # print('validate_psbt_task 1')
        error_msg = e.args[0]
        error_code = Error.PSBT_FRAUDULENT_CHANGE_ERROR
    except psbt.InternalPSBTError as e:
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
        gc.collect()

        await on_done(details, error_msg, error_code)
