# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test PSBT signing-status warnings.

from psbt import psbtObject
from serializations import CTxOut


P2WPKH_SCRIPT = b'\x00\x14' + (b'\x11' * 20)


class FakePrevout:
    n = 0


class FakeTxIn:
    prevout = FakePrevout()


class FakeInput:
    def __init__(self, is_multisig, num_our_keys, fully_signed=False, required_key=None):
        self.is_multisig = is_multisig
        self.num_our_keys = num_our_keys
        self.fully_signed = fully_signed
        self.required_key = required_key
        self.witness_utxo = False
        self.utxo = True
        self.is_segwit = False

    @staticmethod
    def has_utxo():
        return True

    @staticmethod
    def get_utxo(_idx):
        return CTxOut(2000, P2WPKH_SCRIPT)

    @staticmethod
    def determine_my_signing_key(_idx, _utxo, _xfp, _psbt):
        pass


class FakePSBT:
    def __init__(self, inputs):
        self.inputs = inputs
        self.my_xfp = 0
        self.total_value_in = None
        self.fee_is_verified = True
        self.presigned_inputs = set()
        self.num_inputs = len(inputs)
        self.warnings = []

    def input_iter(self):
        for index in range(self.num_inputs):
            yield index, FakeTxIn()


def warnings_for(inputs):
    psbt = FakePSBT(inputs)
    psbtObject.consider_inputs(psbt)
    return psbt.warnings


assert warnings_for([FakeInput(True, 1)]) == [
    ('Partially Signed',
     'Some inputs associated with Passport are already signed. Other signatures are still required: 0')]

assert warnings_for([FakeInput(False, 0), FakeInput(False, 0)]) == [
    ('External Inputs', 'Passport will not sign inputs controlled by another wallet: 0, 1')]

assert warnings_for([
    FakeInput(False, 1, fully_signed=True),
    FakeInput(False, 1, required_key=b'key'),
]) == [
    ('Partially Signed',
     'Some inputs associated with Passport are already signed. Other signatures are still required: 0')]

assert warnings_for([
    FakeInput(False, 0, fully_signed=True),
    FakeInput(False, 1, required_key=b'key'),
]) == [
    ('Partially Signed', 'Some inputs provided were already signed by other parties: 0')]

# A taproot input can have Passport derivation data but no required key when
# it uses an unsupported script path. It must not be described as external.
assert warnings_for([FakeInput(False, 1)]) == [
    ('Partially Signed',
     'Some inputs associated with Passport are already signed. Other signatures are still required: 0')]

assert warnings_for([
    FakeInput(False, 0),
    FakeInput(False, 1),
    FakeInput(False, 0, fully_signed=True),
]) == [
    ('External Inputs', 'Passport will not sign inputs controlled by another wallet: 0'),
    ('Partially Signed',
     'Some inputs associated with Passport are already signed. Other signatures are still required: 1'),
    ('Partially Signed', 'Some inputs provided were already signed by other parties: 2')]

return_value.write(b'OK')
