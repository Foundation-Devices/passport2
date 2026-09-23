# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import common
import history
import pages
import stash
import uasyncio as asyncio
from uio import BytesIO
from ustruct import pack
from ubinascii import unhexlify

from exceptions import FatalPSBTIssue, IncorrectUTXOAmount
from flows import ClearUTXOCacheFlow, SignPsbtCommonFlow
from history import OutptValueCache as Cache
from psbt import psbtInputProxy, psbtObject
from public_constants import PSBT_IN_BIP32_DERIVATION, PSBT_IN_WITNESS_UTXO
from public_constants import PSBT_IN_TAP_BIP32_DERIVATION
from serializations import COutPoint, CTxIn, CTxOut, hash160, ser_compact_size
from taproot import output_script
from tasks.sign_psbt_task import sign_psbt_task


MY_XFP = 0x12345678
PUBKEY = unhexlify('0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798')


class FakeSettings:
    def get(self, key, default=None):
        return default


class FakeFlashCache:
    def __init__(self):
        self.data = {}
        self.writes = 0
        self.saves = 0

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.writes += 1
        self.data[key] = value[:]

    def remove(self, key):
        self.writes += 1
        self.data.pop(key, None)

    def save(self):
        self.saves += 1


class FakeNode:
    def public_key(self):
        return PUBKEY

    def private_key(self):
        return b'\x00' * 31 + b'\x01'


class FakeSensitiveValues:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        pass

    def derive_path(self, path, register=True):
        assert path == 'm/0'
        assert register
        return FakeNode()


def field(kind, value, key=b''):
    key = bytes([kind]) + key
    return ser_compact_size(len(key)) + key + ser_compact_size(len(value)) + value


def make_input(amount, owned=True, pubkey=PUBKEY, taproot=False):
    script = output_script(pubkey[1:], None) if taproot else b'\x00\x14' + hash160(pubkey)
    txout = CTxOut(amount, script)
    data = field(PSBT_IN_WITNESS_UTXO, txout.serialize())
    if owned:
        if taproot:
            data += field(PSBT_IN_TAP_BIP32_DERIVATION, b'\x00' + pack('<II', MY_XFP, 0), pubkey[1:])
        else:
            data += field(PSBT_IN_BIP32_DERIVATION, pack('<II', MY_XFP, 0), pubkey)
    return psbtInputProxy(BytesIO(data + b'\x00'), 0)


class TestPSBT:
    def __init__(self, inputs):
        self.inputs = inputs
        self.my_xfp = MY_XFP
        self.total_value_in = None
        self.fee_is_verified = True
        self.presigned_inputs = set()
        self.num_inputs = len(inputs)
        self.warnings = []
        self.fail_at = None
        for idx, txi in self.input_iter():
            inputs[idx].validate(idx, txi, MY_XFP)

    def input_iter(self):
        for idx in range(self.num_inputs):
            txi = CTxIn()
            txi.prevout = COutPoint(idx + 1, 0)
            yield idx, txi

    def make_txn_segwit_sighash(self, idx, *_args):
        if idx == self.fail_at:
            raise AssertionError('Simulated signing failure')
        return b'\x42' * 32

    make_txn_taproot_sighash = make_txn_segwit_sighash


def assert_raises(exc_type, callback):
    try:
        callback()
    except exc_type:
        return
    raise AssertionError('Expected {}'.format(exc_type))


async def sign(psbt, success=True):
    results = []

    async def on_done(message, error):
        results.append((message, error))

    await sign_psbt_task(on_done, psbt)
    assert len(results) == 1
    if success:
        assert results[0] == (None, None), results
    else:
        assert results[0][1] is not None


class FakeQuestionPage:
    approved = False

    def __init__(self, text, **_kwargs):
        self.text = text

    async def show(self):
        if self.text == 'Sign transaction?':
            return False
        if self.text == 'Cancel this transaction?':
            return True
        assert 'protection' in self.text
        return self.approved


class FakeSuccessPage:
    def __init__(self, text):
        pass

    async def show(self):
        pass


async def run_tests():
    flash = FakeFlashCache()
    replacements = (
        (common, 'settings', FakeSettings()),
        (history, 'flash_cache', flash),
        (stash, 'SensitiveValues', FakeSensitiveValues),
        (stash, 'blank_object', lambda obj: None),
        (pages, 'QuestionPage', FakeQuestionPage),
        (pages, 'SuccessPage', FakeSuccessPage),
    )
    originals = [(module, name, getattr(module, name)) for module, name, _ in replacements]
    original_runtime = Cache.runtime_cache
    original_loaded = Cache._cache_loaded
    try:
        for module, name, replacement in replacements:
            setattr(module, name, replacement)
        Cache.runtime_cache = []
        Cache._cache_loaded = False
        prevout = COutPoint(1, 0)

        # The real input parser and cache must not trust a PSBT rejected by consider_keys.
        malicious = TestPSBT([make_input(9999, owned=False)])
        psbtObject.consider_inputs(malicious)
        assert_raises(FatalPSBTIssue, lambda: psbtObject.consider_keys(malicious))
        assert flash.writes == 0
        assert Cache.fetch_amount(prevout) is None

        # Even valid owned metadata does not authorize a write before approval/signing.
        abandoned = TestPSBT([make_input(8888)])
        psbtObject.consider_inputs(abandoned)
        psbtObject.consider_keys(abandoned)
        review = SignPsbtCommonFlow(0)
        review.psbt = abandoned
        review.goto(review.sign_transaction)
        assert await review.run() is None
        assert abandoned.inputs[0].added_sig is None
        assert flash.writes == 0
        assert Cache.fetch_amount(prevout) is None

        forged = TestPSBT([make_input(7777, pubkey=b'\x03' + PUBKEY[1:])])
        assert_raises(AssertionError, lambda: psbtObject.consider_inputs(forged))
        assert flash.writes == 0

        # A later failure must not record an earlier input whose signature succeeded.
        failed = TestPSBT([make_input(1000), make_input(2000)])
        psbtObject.consider_inputs(failed)
        failed.fail_at = 1
        await sign(failed, success=False)
        assert failed.inputs[0].added_sig
        assert flash.writes == 0

        # Only newly signed owned inputs are recorded, including for a partial PSBT.
        approved = TestPSBT([make_input(1000), make_input(2000, owned=False), make_input(3000)])
        psbtObject.consider_inputs(approved)
        approved.inputs[2].fully_signed = True
        await sign(approved)
        assert approved.inputs[0].added_sig
        assert flash.writes == 1
        assert Cache.fetch_amount(prevout) == 1000
        assert Cache.fetch_amount(COutPoint(2, 0)) is None
        assert Cache.fetch_amount(COutPoint(3, 0)) is None

        # Re-signing the same amount must not duplicate entries or cause FIFO eviction.
        repeated = TestPSBT([make_input(1000)])
        psbtObject.consider_inputs(repeated)
        await sign(repeated)
        assert flash.writes == 1
        assert len(Cache.runtime_cache) == 1

        # Reload the saved representation and retain the SegWit fee-attack defense.
        Cache.runtime_cache = []
        Cache._cache_loaded = False
        changed = TestPSBT([make_input(1001)])
        assert_raises(IncorrectUTXOAmount, lambda: psbtObject.consider_inputs(changed))
        await sign(changed, success=False)
        assert changed.inputs[0].added_sig is None
        assert flash.writes == 1
        assert Cache.fetch_amount(prevout) == 1000

        # Cancelling reset preserves protection; confirming removes memory and saved data.
        assert await ClearUTXOCacheFlow().run() is False
        assert Cache.fetch_amount(prevout) == 1000
        assert flash.writes == 1
        FakeQuestionPage.approved = True
        assert await ClearUTXOCacheFlow().run() is True
        assert flash.saves == 1
        assert Cache.KEY not in flash.data
        assert Cache.runtime_cache == []
        Cache._cache_loaded = False
        assert Cache.fetch_amount(prevout) is None

        recovered = TestPSBT([make_input(1001)])
        psbtObject.consider_inputs(recovered)
        await sign(recovered)
        assert Cache.fetch_amount(prevout) == 1001

        # Taproot signatures use the same recording boundary as ECDSA signatures.
        Cache.clear()
        taproot = TestPSBT([make_input(4000, taproot=True)])
        psbtObject.consider_inputs(taproot)
        assert Cache.fetch_amount(prevout) is None
        await sign(taproot)
        assert taproot.inputs[0].tap_key_sig
        assert Cache.fetch_amount(prevout) == 4000
        return_value.write(b'OK')
    finally:
        for module, name, original in originals:
            setattr(module, name, original)
        Cache.runtime_cache = original_runtime
        Cache._cache_loaded = original_loaded


asyncio.run(run_tests())
