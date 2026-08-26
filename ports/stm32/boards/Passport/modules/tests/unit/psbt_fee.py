# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test PSBT input-value validation and fee review rendering.

from uio import BytesIO
from ustruct import pack

import history
import stash
from flows.sign_psbt_common_flow import SignPsbtCommonFlow
from psbt import psbtInputProxy, psbtObject
from public_constants import (
    PSBT_IN_BIP32_DERIVATION,
    PSBT_IN_NON_WITNESS_UTXO,
    PSBT_IN_WITNESS_UTXO,
)
from serializations import CTxOut, hash160, ser_compact_size


P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)
MY_XFP = 0x12345678
OWNED_PUBKEY = b'\x02' + (b'\x55' * 32)
FORGED_PUBKEY = b'\x03' + (b'\x66' * 32)


def psbt_field(key_type, value, key=b''):
    full_key = bytes([key_type]) + key
    return ser_compact_size(len(full_key)) + full_key + ser_compact_size(len(value)) + value


def previous_tx(txout):
    txin = (b'\x00' * 32) + pack('<I', 0) + b'\x00' + pack('<I', 0xffffffff)
    return pack('<i', 2) + b'\x01' + txin + b'\x01' + txout.serialize() + pack('<I', 0)


def make_input(witness_txout, non_witness_txout=None):
    data = b''
    if non_witness_txout:
        data += psbt_field(PSBT_IN_NON_WITNESS_UTXO, previous_tx(non_witness_txout))
    data += psbt_field(PSBT_IN_WITNESS_UTXO, witness_txout.serialize())
    return psbtInputProxy(BytesIO(data + b'\x00'), 0)


def make_owned_input(pubkey=OWNED_PUBKEY):
    txout = CTxOut(2000, b'\x00\x14' + hash160(pubkey))
    data = psbt_field(PSBT_IN_WITNESS_UTXO, txout.serialize())
    data += psbt_field(PSBT_IN_BIP32_DERIVATION, pack('<II', MY_XFP, 0), pubkey)
    return psbtInputProxy(BytesIO(data + b'\x00'), 0)


def assert_raises(exc_type, callback):
    try:
        callback()
    except exc_type:
        return
    raise AssertionError('Expected {}'.format(exc_type))


matching = CTxOut(1000, P2WPKH_SCRIPT)
matching_input = make_input(matching, matching)
loaded = matching_input.get_utxo(0)
assert loaded.nValue == matching.nValue
assert loaded.scriptPubKey == matching.scriptPubKey
assert matching_input.is_segwit

amount_mismatch = make_input(CTxOut(999, P2WPKH_SCRIPT), matching)
assert_raises(AssertionError, lambda: amount_mismatch.get_utxo(0))

script_mismatch = make_input(CTxOut(1000, b'\x00\x14' + (b'\x33' * 20)), matching)
assert_raises(AssertionError, lambda: script_mismatch.get_utxo(0))


class FakePrevout:
    n = 0


class FakeTxIn:
    prevout = FakePrevout()


class FakeNode:
    @staticmethod
    def public_key():
        return OWNED_PUBKEY


class FakeSensitiveValues:
    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc, _traceback):
        pass

    @staticmethod
    def derive_path(path, register=False):
        assert path == 'm/0'
        assert not register
        return FakeNode()


class FakeInputPSBT:
    def __init__(self, psbt_input, my_xfp=0):
        self.inputs = [psbt_input]
        self.my_xfp = my_xfp
        self.total_value_in = None
        self.fee_is_verified = True
        self.presigned_inputs = set()
        self.num_inputs = 1
        self.warnings = []

    def input_iter(self):
        yield 0, FakeTxIn()


verified_amounts = []
original_verify_amount = history.verify_amount
original_sensitive_values = stash.SensitiveValues
history.verify_amount = lambda _prevout, amount, idx: verified_amounts.append((amount, idx))
stash.SensitiveValues = FakeSensitiveValues
try:
    external_input_psbt = FakeInputPSBT(make_input(CTxOut(2000, P2WPKH_SCRIPT)))
    psbtObject.consider_inputs(external_input_psbt)
    assert not external_input_psbt.fee_is_verified

    owned_input = make_owned_input()
    owned_input.validate(0, FakeTxIn(), MY_XFP)
    owned_input_psbt = FakeInputPSBT(owned_input, MY_XFP)
    psbtObject.consider_inputs(owned_input_psbt)
    assert owned_input_psbt.fee_is_verified
    assert owned_input.num_our_keys == 1
    assert owned_input.required_key == OWNED_PUBKEY

    forged_input = make_owned_input(FORGED_PUBKEY)
    forged_input.validate(0, FakeTxIn(), MY_XFP)
    forged_input_psbt = FakeInputPSBT(forged_input, MY_XFP)
    assert_raises(AssertionError, lambda: psbtObject.consider_inputs(forged_input_psbt))
finally:
    history.verify_amount = original_verify_amount
    stash.SensitiveValues = original_sensitive_values

assert verified_amounts == [(2000, 0), (2000, 0)]


class FakeOutputProxy:
    is_change = False

    def validate(self, _idx, _txout, _xfp, _active_multisig):
        pass


class FakeOutputPSBT:
    def __init__(self, fee_is_verified):
        self.outputs = [FakeOutputProxy()]
        self.total_value_out = 1000
        self.total_value_in = 5000
        self.fee_is_verified = fee_is_verified
        self.self_send = False
        self.warnings = []
        self.my_xfp = 0
        self.active_multisig = None

    def output_iter(self):
        yield 0, CTxOut(self.total_value_out, P2WPKH_SCRIPT)

    def calculate_fee(self):
        return self.total_value_in - self.total_value_out

    def consider_dangerous_change(self, _xfp):
        pass


unverified_fee_psbt = FakeOutputPSBT(external_input_psbt.fee_is_verified)
psbtObject.consider_outputs(unverified_fee_psbt)
assert unverified_fee_psbt.warnings[0][0] == 'Unverified Fee'
assert all(label not in {'Big Fee', 'Huge Fee'} for label, _text in unverified_fee_psbt.warnings)

verified_fee_psbt = FakeOutputPSBT(owned_input_psbt.fee_is_verified)
psbtObject.consider_outputs(verified_fee_psbt)
assert verified_fee_psbt.warnings[0][0] == 'Huge Fee'


class FakeChain:
    def render_value(self, value):
        return str(value), 'sats'


class FakeFlow:
    chain = FakeChain()

    def __init__(self, psbt):
        self.psbt = psbt


review = SignPsbtCommonFlow.render_warnings(FakeFlow(unverified_fee_psbt))
assert 'Unverified' in review
assert '4000 sats' not in review

review = SignPsbtCommonFlow.render_warnings(FakeFlow(verified_fee_psbt))
assert '4000 sats' in review

return_value.write(b'OK')
