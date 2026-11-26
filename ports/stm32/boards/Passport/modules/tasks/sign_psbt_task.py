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
    from utils import keypath_to_str
    from serializations import ser_sig_der
    import stash
    import gc
    from foundation import secp256k1
    from taproot import taproot_sign_key
    from psbt import derive_from_parent, _InputTable
    import history

    try:
        with stash.SensitiveValues() as sv:
            error_msg = None
            error_code = None
            # Account-level nodes, derived once and wiped when the session ends.
            parents = {}

            # Inputs are parsed from flash again below, so flash must still hold the
            # PSBT that was validated and reviewed.
            psbt.check_unchanged()
            await psbt.reserve_signatures()

            # Sign individual inputs
            # One bit per input we signed.
            success = bytearray((psbt.num_inputs + 7) // 8)
            for in_idx, txi in psbt.input_iter():
                # print('PROGRESS: {}% (in_idx={}'.format(int(in_idx * 100 / psbt.num_inputs), in_idx))
                # Every 10 inputs: nothing is kept per input, so collecting after each
                # one costs time without saving memory.
                if in_idx % 10 == 0:
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

                if not inp.is_multisig:
                    assert not (inp.added_sig or inp.tap_key_sig), \
                        "This transaction has already been signed"

                # Rebuild the scripts this signature commits to from the validated
                # bytes, and sign for the amount the user reviewed.
                utxo = inp.get_utxo(txi.prevout.n)
                if utxo.nValue != inp.amount:
                    raise AssertionError('Input #%d changed after it was checked' % in_idx)
                script_sig, script_code = inp.signing_scripts(utxo, in_idx)
                txi.scriptSig = script_sig
                if not txi.scriptSig:
                    raise AssertionError('No scriptsig?')

                if inp.is_segwit:
                    history.verify_amount(txi.prevout, inp.amount, in_idx)

                if inp.policy_spend_plan:
                    inp.policy_spend_plan.assert_p2wsh_scope(
                        in_idx, inp.subpaths, utxo.scriptPubKey,
                        inp.get(inp.witness_script), inp.sighash,
                        inp.required_key, inp.part_sig)
                del utxo

                if not inp.is_segwit:
                    # Hash by serializing/blanking various subparts of the transaction
                    digest = psbt.make_txn_sighash(in_idx, txi, inp.sighash)
                elif len(inp.tap_subpaths) > 0:
                    # TODO: add annex and ext_flag
                    digest = psbt.make_txn_taproot_sighash(in_idx, inp.sighash)
                else:
                    # Hash the inputs and such in totally new ways, based on BIP-143
                    digest = psbt.make_txn_segwit_sighash(in_idx, txi,
                                                          inp.amount, script_code, inp.sighash)

                policy_multisig = inp.is_multisig and inp.policy_spend_plan is not None
                if policy_multisig:
                    signing_keys = tuple(sorted(inp.required_key))
                    added_sigs = {}
                else:
                    # Existing wallet types keep their ownership-based key selection.
                    signing_keys = (None,)

                for which_key in signing_keys:
                    if policy_multisig:
                        # The spend plan above binds every required key to its path.
                        skp = keypath_to_str(inp.subpaths[which_key])
                        node = derive_from_parent(sv, inp.subpaths[which_key], parents)
                    else:
                        node, which_key = inp.get_signing_node(sv, psbt.my_xfp, in_idx, parents)

                    try:
                        if policy_multisig and node.public_key() != which_key:
                            raise AssertionError(
                                "Path (%s) led to wrong pubkey for input #%d" % (skp, in_idx))

                        pk = node.private_key()
                        try:
                            if len(inp.tap_subpaths) > 0:
                                # BIP86 Taproot key-path signature.
                                inp.tap_key_sig = taproot_sign_key(
                                    None, pk, inp.sighash, digest)
                            else:
                                result = secp256k1.sign_ecdsa(digest, pk)
                                try:
                                    if len(result) != 64:
                                        raise AssertionError('Incorrect signature length.')
                                    der_sig = ser_sig_der(
                                        result[0:32], result[32:64], inp.sighash)
                                    if policy_multisig:
                                        if which_key in added_sigs:
                                            raise AssertionError(
                                                'This multisig key has already been signed')
                                        added_sigs[which_key] = der_sig
                                    else:
                                        inp.added_sig = (which_key, der_sig)
                                finally:
                                    del result
                        finally:
                            stash.blank_object(pk)
                    finally:
                        stash.blank_object(node)
                    del pk, node

                if policy_multisig:
                    inp.added_sigs = added_sigs

                # print("result %s" % b2a_hex(result).decode('ascii'))

                success[in_idx >> 3] |= 1 << (in_idx & 7)
                del inp

            # And again once every signature is made, before any of them is used.
            psbt.check_unchanged()

        # No cache writes until every signature succeeds. The success set only
        # includes inputs whose signing keys we derived and verified above.

        def signed_amounts():
            # The input table already holds each input's checked amount and type, so
            # read them there rather than parsing every input from flash again.
            table = psbt.inputs if isinstance(psbt.inputs, _InputTable) else None
            for in_idx, txi in psbt.input_iter():
                if not success[in_idx >> 3] & (1 << (in_idx & 7)):
                    continue
                if table is not None:
                    amount = table.segwit_amount(in_idx)
                    if amount is not None:
                        yield txi.prevout, amount, in_idx
                else:
                    inp = psbt.inputs[in_idx]
                    if inp.is_segwit:
                        yield txi.prevout, inp.amount, in_idx

        history.OutptValueCache.record_amounts(signed_amounts())

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
        # A bare assert carries no args, so fall back to a message of our own
        error_msg = e.args[0] if e.args else 'Unable to sign transaction.'
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
