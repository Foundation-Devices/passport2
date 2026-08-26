# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
# SPDX-License-Identifier: GPL-3.0-only
#
# (c) Copyright 2018 by Coinkite Inc. This file is part of Coldcard <coldcardwallet.com>
# and is covered by GPLv3 license found in COPYING.
#
# sign_psbt_task.py - Sign a PSBT that is in external SPI flash


async def sign_psbt_task(on_done, psbt):
    from exceptions import FraudulentChangeOutput, FatalPSBTIssue
    from errors import Error
    from serializations import ser_sig_der
    import stash
    import gc
    from foundation import secp256k1
    from taproot import taproot_sign_key

    try:
        with stash.SensitiveValues() as sv:
            error_msg = None
            error_code = None

            # Sign individual inputs
            sigs = 0
            success = set()
            for in_idx, txi in psbt.input_iter():
                # print('PROGRESS: {}% (in_idx={}'.format(int(in_idx * 100 / psbt.num_inputs), in_idx))
                gc.collect()

                inp = psbt.inputs[in_idx]

                if not inp.has_utxo():
                    # maybe they didn't provide the UTXO
                    continue

                if not inp.required_key:
                    # we don't know the key for this input
                    continue

                if inp.fully_signed:
                    # for multisig, it's possible I need to add another sig
                    # but in other cases, no more signatures are possible
                    continue

                txi.scriptSig = inp.scriptSig
                if not txi.scriptSig:
                    raise AssertionError('No scriptsig?')

                if not inp.is_segwit:
                    # Hash by serializing/blanking various subparts of the transaction
                    digest = psbt.make_txn_sighash(in_idx, txi, inp.sighash)
                elif len(inp.tap_subpaths) > 0:
                    # TODO: add annex and ext_flag
                    digest = psbt.make_txn_taproot_sighash(in_idx, inp.sighash)
                else:
                    # Hash the inputs and such in totally new ways, based on BIP-143
                    digest = psbt.make_txn_segwit_sighash(in_idx, txi,
                                                          inp.amount, inp.scriptCode, inp.sighash)

                node, which_key = inp.get_signing_node(sv, psbt.my_xfp, in_idx)

                if not inp.is_multisig:
                    assert not (inp.added_sig or inp.tap_key_sig), \
                        "This transaction has already been signed"

                # The precious private key we need
                pk = node.private_key()

                # print("privkey %s" % b2a_hex(pk).decode('ascii'))
                # print(" pubkey %s" % b2a_hex(which_key).decode('ascii'))
                # print(" digest %s" % b2a_hex(digest).decode('ascii'))

                # Do the ACTUAL signature ... finally!!!
                if len(inp.tap_subpaths) > 0:
                    # TODO: handle taproot scripts
                    inp.tap_key_sig = taproot_sign_key(None, pk, inp.sighash, digest)
                else:
                    result = secp256k1.sign_ecdsa(digest, pk)

                    # convert signature to DER format
                    if len(result) != 64:
                        raise AssertionError('Incorrect signature length.')

                    r = result[0:32]
                    s = result[32:64]

                    inp.added_sig = (which_key, ser_sig_der(r, s, inp.sighash))

                    # Memory cleanup
                    del result, r, s

                # private key no longer required
                stash.blank_object(pk)
                stash.blank_object(node)
                del pk, node, pu, skp

                # print("result %s" % b2a_hex(result).decode('ascii'))

                success.add(in_idx)

        # All went well, so just fall through and call on_done()

    except FraudulentChangeOutput as e:
        # print('FraudulentChangeOutput: {}'.format(e))
        error_msg = e.args[0]
        error_code = Error.PSBT_FRAUDULENT_CHANGE_ERROR
    except FatalPSBTIssue as e:
        # print('FatalPSBTIssue: {}'.format(e))
        error_msg = e.args[0]
        error_code = Error.PSBT_FATAL_ERROR
    except AssertionError as e:
        # print('AssertionError: {}'.format(e))
        error_msg = e.args[0]
        error_code = Error.PSBT_FATAL_ERROR
    except MemoryError as e:
        # print('MemoryError: {}'.format(e))
        error_msg = 'Transaction is too complex.'
        error_code = Error.OUT_OF_MEMORY_ERROR
    except BaseException as e:
        # print('BaseException: {}'.format(e))
        error_msg = 'Invalid PSBT.'
        error_code = Error.PSBT_FATAL_ERROR
    finally:
        # print('finally...')
        gc.collect()

    await on_done(error_msg, error_code)
