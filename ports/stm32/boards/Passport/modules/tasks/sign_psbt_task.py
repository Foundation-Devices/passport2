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
    from utils import keypath_to_str, swab32
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

                if inp.is_multisig:
                    # need to consider a set of possible keys, since xfp may not be unique
                    for which_key in inp.required_key:
                        # get node required
                        skp = keypath_to_str(inp.subpaths[which_key])
                        node = sv.derive_path(skp, register=False)

                        # expensive test, but works... and important
                        pu = node.public_key()
                        if pu == which_key:
                            break
                    else:
                        raise AssertionError("Input #%d needs pubkey this Passport doesn't have." % in_idx)

                else:
                    # single pubkey <=> single key
                    which_key = inp.required_key

                    assert not inp.added_sig, "already done??"
                    assert not inp.tap_key_sig, "already done taproot??"

                    if len(inp.subpaths) > 0 and \
                        (inp.subpaths[which_key][0] == psbt.my_xfp or
                         inp.subpaths[which_key][0] == swab32(psbt.my_xfp)):

                        # get node required
                        skp = keypath_to_str(inp.subpaths[which_key])
                        node = sv.derive_path(skp, register=False)

                        # expensive test, but works... and important
                        pu = node.public_key()

                    # tap_subpaths have type ([path_elements], [tap_hashes])
                    elif len(inp.tap_subpaths) > 0 and \
                        (inp.tap_subpaths[which_key][0][0] == psbt.my_xfp or
                         inp.tap_subpaths[which_key][0][0] == swab32(psbt.my_xfp)):

                        # get node required
                        skp = keypath_to_str(inp.tap_subpaths[which_key][0])
                        node = sv.derive_path(skp, register=False)

                        # expensive test, but works... and important
                        pu = node.public_key()[1:]

                    if pu != which_key:
                        raise AssertionError("Path (%s) led to wrong pubkey for input #%d" % (skp, in_idx))

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
