# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reject Taproot script-path policies and preserve BIP86 signing."""

import uasyncio
from ubinascii import a2b_base64, unhexlify
from uio import BytesIO

import common
import history
import stash
from exceptions import FatalPSBTIssue
from psbt import psbtObject
from tasks.sign_psbt_task import sign_psbt_task
from wallet_policy import KeyInfo


class MemorySettings:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


if common.settings is None:
    common.settings = MemorySettings()


class FixturePublicValues:
    """Stand in for the keystore using the fixture's owned account xpub."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def derive_path(self, path, register=True):
        import chains
        from public_constants import AF_CLASSIC
        from utils import str_to_keypath

        key = KeyInfo.parse(OWNED_KEY)
        numeric_path = str_to_keypath(0, path)[1:]
        assert tuple(numeric_path[:len(key.path)]) == key.path
        node = chains.current_chain().deserialize_node(key.xpub, AF_CLASSIC)
        for index in numeric_path[len(key.path):]:
            node.derive(index, True)
        return node


OWNED_KEY = (
    "[5a3469b6/86'/0'/0']"
    'xpub6Cx47kkB7dkMy515HJa3WH2iRSqqScxnsstoSqF1NEyjXKC7N2vTBqVjx1LZ'
    'Ab6hVhEdunJYTxNShqgo9rZ4DEV7rWGazkkzck7vjxjKdLu'
)
KEY_PATH_PRIVATE_KEY = unhexlify(
    '523dcb3ce6a2802987e5df1e6beb14057b311c0eaa9779355817bcc593a45a57')
KEY_PATH_PUBKEY = unhexlify(
    '15935d7f96add7901be6451be8e1037071da1b95d45c56155448700227f163e9')
KEY_PATH_DIGEST = unhexlify(
    'b00a9cac35d66d9f277987b776bb78069384344ce3c579622b5108251822c71b')
PSBT_BASE64 = (
    'cHNidP8BAH0CAAAAARERERERERERERERERERERERERERERERERERERERERERAAAAAAD+////ApBfAQAAAAAAFgAUVLa1Ho5v'
    't/N4um+vD82arsZZH+MoIwAAAAAAACJRIEVz5qpI3J5RutKQoUrN75B+kEjlJkjB3rYNI1M4iY11AAAAAAABASughgEAAAAA'
    'ACJRIGjZ8StNc9kVB8bWEPA7kflWi59g73D1w6nQGbhubbB0IhXAeb5mfvncu6xVoGKVzocLBwKb/NstzijZWfKBWxb4F5'
    'gjIA4D0nc6v/yD2GZZJlrNW0B19F8h7h2S0kBafGiWfqkxrMAhFg4D0nc6v/yD2GZZJlrNW0B19F8h7h2S0kBafGiWfqkx'
    'OQFFQzGr8V4kxuZDLRG3tQePZR5tLGWVfPpM741TLzCsPFo0abZWAACAAAAAgAAAAIAAAAAABQAAAAEXIHm+Zn753LusVaBi'
    'lc6HCwcCm/zbLc4o2VnygVsW+BeYARggRUMxq/FeJMbmQy0Rt7UHj2UebSxllXz6TO+NUy8wrDwAAQYlAMAiINZluScGyEB'
    'SObx+96oxmOUWwPVVLbM7MQvoVUl7/kwYrAABBSB5vmZ++dy7rFWgYpXOhwsHApv82y3OKNlZ8oFbFvgXmCEH1mW5JwbIQ'
    'FI5vH73qjGY5RbA9VUtszsxC+hVSXv+TBg5AYy9eilgnkg4nY6kSUC/rxSebzjtDHQMNYgUyTAp9tOsWjRptlYAAIAAAACA'
    'AAAAgAEAAAAGAAAAAQYlAMAiINZluScGyEBSObx+96oxmOUWwPVVLbM7MQvoVUl7/kwYrAA='
)
KEY_PATH_PSBT_BASE64 = (
    'cHNidP8BAFICAAAAASIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiIiAQAAAAD9////AWi/AAAAAAAAFgAU9ZNq0AVK'
    'dnF4n/pYyvTKWK7JMqEAAAAAAAEBK1DDAAAAAAAAIlEgsQCqISnbf8Y1iBjWxeSsmAv6Re+Vd3z+4stdzJqaA5YhFhWTXX+W'
    'rdeQG+ZFG+jhA3Bx2huV1FxWFVRIcAIn8WPpGQBaNGm2VgAAgAAAAIAAAACAAAAAAAcAAAABFyAVk11/lq3XkBvmRRvo4QNw'
    'cdobldRcVhVUSHACJ/Fj6QAA'
)


async def run_test():
    common.settings.set('chain', 'BTC')
    common.settings.set('xfp', 3060347994)
    common.settings.set('wallet_policies', [])
    history.verify_amount = lambda *args: None

    # Script-path PSBTs remain unsupported even with valid scripts/derivations.
    parsed = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await parsed.validate()
    try:
        parsed.consider_inputs()
        assert False, 'Taproot script-path input was accepted'
    except FatalPSBTIssue as exc:
        assert 'script-path signing is not supported' in str(exc)

    original_sensitive_values = stash.SensitiveValues
    original_blank_object = stash.blank_object

    # Existing BIP86 key-path detection, sighash, and signing remain supported.
    key_path = psbtObject.read_psbt(BytesIO(a2b_base64(KEY_PATH_PSBT_BASE64)))
    await key_path.validate()
    key_path.consider_inputs()
    key_path.consider_keys()
    key_input = key_path.inputs[0]
    assert key_path.active_policy is None
    assert key_input.policy_spend_plan is None
    assert key_input.required_key == KEY_PATH_PUBKEY
    assert not key_input.is_multisig
    assert key_path.make_txn_taproot_sighash(0, 0) == KEY_PATH_DIGEST

    class KeyPathNode:
        def public_key(self):
            return b'\x02' + KEY_PATH_PUBKEY

        def private_key(self):
            return bytearray(KEY_PATH_PRIVATE_KEY)

    class KeyPathValues(FixturePublicValues):
        def derive_path(self, path, register=False):
            return KeyPathNode()

    key_path_result = []

    async def key_path_done(error_msg, error_code):
        key_path_result.append((error_msg, error_code))

    stash.SensitiveValues = KeyPathValues
    stash.blank_object = lambda value: None
    try:
        await sign_psbt_task(key_path_done, key_path)
    finally:
        stash.SensitiveValues = original_sensitive_values
        stash.blank_object = original_blank_object
    assert key_path_result == [(None, None)]
    assert len(key_input.tap_key_sig) == 64


original_sensitive_values = stash.SensitiveValues
stash.SensitiveValues = FixturePublicValues
try:
    uasyncio.run(run_test())
finally:
    stash.SensitiveValues = original_sensitive_values
