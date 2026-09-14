# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Test wallet approval and change verification before transaction review.

import common
import flows
import pages
import stash
import utils
import uasyncio as asyncio
from flows import Flow, SignPsbtCommonFlow
from flows import sign_psbt_common_flow
from public_constants import MUSIG_ASK, MUSIG_SKIP
from ubinascii import unhexlify
from utils import get_multisig_policy, str_to_keypath


MY_XFP = 0x12345678
OTHER_KEY = unhexlify('02c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5')
PATHS = ("m/84'/0'/0'/1/7", "m/86'/0'/0'/1/7", "m/48'/0'/0'/2'/1/7")
# Precomputed fixtures from test seed bytes(range(32)); this test does not derive keys.
OWNED_KEYS = (
    unhexlify('02477e5978ac99be533333b444e635fdee1001992c01dec8c41327cdb9a7d7b2a1'),
    unhexlify('03bdb8d2c655d9d1fb6ff6533b43660033e5c23b2ca4b290223d813f08407d6bdb'),
    unhexlify('03505e71bc8f2aa762c561194bf3aa6c315fb07a0cf63fd631e43a6a2c17674105'),
)
events = []


class FakeImportMultisigWalletFlow:
    result = None
    calls = 0

    def __init__(self, wallet):
        assert wallet == 'proposed-wallet'
        FakeImportMultisigWalletFlow.calls += 1

    async def run(self):
        events.append('import')
        return self.result


class FakePsbt:
    def __init__(self, needs_approval):
        self.multisig_import_needs_approval = needs_approval
        self.active_multisig = 'proposed-wallet'
        self.my_xfp = MY_XFP
        self.outputs = []


class FakeOutput:
    is_change = True

    def __init__(self, path, key):
        self.subpaths = {}
        self.tap_subpaths = {}
        if path == PATHS[1]:
            self.tap_subpaths[key[1:]] = (str_to_keypath(MY_XFP, path), [])
        else:
            if path == PATHS[2]:
                # The other cosigner must not be mistaken for our ownership proof.
                self.subpaths[b'\x03' + OTHER_KEY[1:]] = str_to_keypath(0xabcdef01, path)
            self.subpaths[key] = str_to_keypath(MY_XFP, path)


class FakeNode:
    def __init__(self, key):
        self.key = key

    def public_key(self):
        return self.key


class FakeSensitiveValues:
    def __enter__(self):
        events.append('verify')
        return self

    def __exit__(self, *_args):
        events.append('clear')

    def derive_path(self, path):
        assert path in PATHS
        events.append(path)
        return FakeNode(OWNED_KEYS[PATHS.index(path)])


class FakeErrorPage:
    def __init__(self, text):
        assert "BIP32 path doesn't match" in text

    async def show(self):
        events.append('error')


class FakeQuestionPage:
    def __init__(self, **_kwargs):
        pass

    async def show(self):
        events.append('confirm')
        return True


async def fake_spinner_task(_text, task, args=()):
    results = []

    async def on_done(*result):
        results.append(result)

    await task(on_done, *args)
    assert len(results) == 1
    return results[0]


async def fake_sign_psbt_task(on_done, _psbt):
    events.append('sign')
    await on_done(None, None)


class FakeSettings:
    temporary_mode = True

    def __init__(self, policy=None):
        self.policy = policy

    def get(self, key, default=None):
        if key == 'temporary_seed':
            return 'temporary-seed'
        if key == 'multisig_policy' and self.policy is not None:
            return self.policy
        return default


class FakeSignFlow(SignPsbtCommonFlow):
    def __init__(self, needs_approval):
        # Exercise state ordering without rendering pages or accessing device settings.
        Flow.__init__(self, initial_state=self.check_multisig_import)
        self.psbt = FakePsbt(needs_approval)
        self.cancel_review = False

    async def show_transaction_details(self):
        events.append('review')
        if self.cancel_review:
            self.set_result(None)
        else:
            self.goto(self.sign_transaction)


async def run_tests():
    original_settings = common.settings
    replacements = (
        (flows, 'ImportMultisigWalletFlow', FakeImportMultisigWalletFlow),
        (pages, 'ErrorPage', FakeErrorPage),
        (pages, 'QuestionPage', FakeQuestionPage),
        (stash, 'SensitiveValues', FakeSensitiveValues),
        (utils, 'spinner_task', fake_spinner_task),
        (sign_psbt_common_flow, 'spinner_task', fake_spinner_task),
        (sign_psbt_common_flow, 'sign_psbt_task', fake_sign_psbt_task),
    )
    originals = [(module, name, getattr(module, name)) for module, name, _ in replacements]

    try:
        for module, name, replacement in replacements:
            setattr(module, name, replacement)

        FakeImportMultisigWalletFlow.result = False
        FakeImportMultisigWalletFlow.calls = 0
        events.clear()
        flow = FakeSignFlow(needs_approval=True)
        assert await flow.run() is None
        assert FakeImportMultisigWalletFlow.calls == 1
        assert events == ['import']

        FakeImportMultisigWalletFlow.result = True
        for needs_approval in (True, False):
            events.clear()
            flow = FakeSignFlow(needs_approval)
            flow.psbt.outputs = [FakeOutput(PATHS[0], OWNED_KEYS[0])]
            assert await flow.run() is flow.psbt
            expected = ['import'] if needs_approval else []
            assert events == expected + ['verify', PATHS[0], 'clear', 'review', 'confirm', 'sign']

        # Reviewing and cancelling a transaction without change must not open the key store.
        payment = FakeOutput(PATHS[0], OTHER_KEY)
        payment.is_change = False
        for outputs in ([], [payment]):
            events.clear()
            flow = FakeSignFlow(needs_approval=False)
            flow.psbt.outputs = outputs
            flow.cancel_review = True
            assert await flow.run() is None
            assert events == ['review']

        events.clear()
        flow = FakeSignFlow(needs_approval=False)
        flow.psbt.outputs = [FakeOutput(PATHS[0], OWNED_KEYS[0])]
        flow.cancel_review = True
        assert await flow.run() is None
        assert events == ['verify', PATHS[0], 'clear', 'review']

        # Exercise the real ownership task and flow, with only the key store and UI replaced.
        # Its sensitive-value context must close before review, and run just once.
        for path, owned_key in zip(PATHS, OWNED_KEYS):
            for key in (owned_key, OTHER_KEY):
                events.clear()
                flow = FakeSignFlow(needs_approval=False)
                flow.psbt.outputs = [FakeOutput(path, key)]
                result = await flow.run()
                if key == owned_key:
                    assert result is flow.psbt
                    assert events == ['verify', path, 'clear', 'review', 'confirm', 'sign']
                else:
                    assert result is None
                    assert events == ['verify', path, 'clear', 'error']

        common.settings = FakeSettings()
        assert get_multisig_policy() == MUSIG_ASK

        common.settings = FakeSettings(policy=MUSIG_SKIP)
        assert get_multisig_policy() == MUSIG_SKIP

        return_value.write(b'OK')
    finally:
        for module, name, original in originals:
            setattr(module, name, original)
        common.settings = original_settings


asyncio.run(run_tests())
