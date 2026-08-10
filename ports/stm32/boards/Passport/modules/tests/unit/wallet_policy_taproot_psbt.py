# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""MicroPython integration test for registered Taproot script-path policies."""

import uasyncio
from ubinascii import a2b_base64, unhexlify
from uio import BytesIO

import common
import history
import stash
from exceptions import FatalPSBTIssue, FraudulentChangeOutput
from psbt import psbtObject
from tasks.sign_psbt_task import sign_psbt_task
from wallet_policy import MiniscriptPolicy


class MemorySettings:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


if common.settings is None:
    common.settings = MemorySettings()


OWNED_KEY = (
    "[5a3469b6/86'/0'/0']"
    'xpub6Cx47kkB7dkMy515HJa3WH2iRSqqScxnsstoSqF1NEyjXKC7N2vTBqVjx1LZ'
    'Ab6hVhEdunJYTxNShqgo9rZ4DEV7rWGazkkzck7vjxjKdLu'
)
INTERNAL_KEY = (
    '79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798'
)
PRIVATE_KEY = unhexlify(
    'b12edd4a0724a4110f0a85bd8be7e29ccdc017a006b677986e3e5218e2b5c763')
EXPECTED_DIGEST = unhexlify(
    'e69c21b9239c96576a816674518215489d4ea8e0c7d48e375f0dda07e0a78cff')
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


async def parse_policy_psbt(policy):
    parsed = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await parsed.validate()
    history.verify_amount = lambda *args: None
    parsed.consider_inputs()
    parsed.consider_keys()
    parsed.consider_outputs()
    return parsed


async def run_test():
    policy = MiniscriptPolicy(
        'Tap Recovery', 'BTC',
        'tr({},pk(@0/**))'.format(INTERNAL_KEY), (OWNED_KEY,), (0,))
    common.settings.set('chain', 'BTC')
    common.settings.set('xfp', 3060347994)
    common.settings.set('wallet_policies', [policy.serialize()])

    parsed = await parse_policy_psbt(policy)
    assert parsed.active_policy.policy_id == policy.policy_id
    plan = parsed.inputs[0].policy_spend_plan
    assert plan.script_context == 'tapscript'
    assert plan.branch == 0 and plan.address_index == 5
    assert parsed.inputs[0].required_key == plan.expected_pubkey
    assert parsed.outputs[1].is_change
    assert parsed.outputs[1].policy_branch == 1
    assert parsed.outputs[1].policy_address_index == 6

    digest = parsed.make_txn_taproot_sighash(
        0, 0, ext_flag=1, tapleaf_hash=plan.tapleaf_hash)
    assert digest == EXPECTED_DIGEST

    class SigningNode:
        def public_key(self):
            return b'\x02' + plan.expected_pubkey

        def private_key(self):
            return bytearray(PRIVATE_KEY)

    class SigningValues:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def derive_path(self, path, register=False):
            return SigningNode()

    result = []

    async def on_done(error_msg, error_code):
        result.append((error_msg, error_code))

    original_sensitive_values = stash.SensitiveValues
    original_blank_object = stash.blank_object
    stash.SensitiveValues = SigningValues
    stash.blank_object = lambda value: None
    try:
        await sign_psbt_task(on_done, parsed)

        # Mutating a validated scope before the private-key boundary must be
        # detected by the immutable SpendPlan recheck in the signing task.
        changed_after_validation = await parse_policy_psbt(policy)
        changed_input = changed_after_validation.inputs[0]
        owned_pubkey = changed_input.policy_spend_plan.expected_pubkey
        path, _ = changed_input.tap_subpaths[owned_pubkey]
        changed_input.tap_subpaths[owned_pubkey] = (path, (bytes(32),))
        rejected = []

        async def rejected_done(error_msg, error_code):
            rejected.append((error_msg, error_code))

        await sign_psbt_task(rejected_done, changed_after_validation)
        assert rejected and rejected[0][0] is not None
        assert changed_input.added_tap_script_sig is None
    finally:
        stash.SensitiveValues = original_sensitive_values
        stash.blank_object = original_blank_object
    assert result == [(None, None)]
    signature_key, signature = parsed.inputs[0].added_tap_script_sig
    assert len(signature) == 64

    # Ensure script-path fields survive serialization and the new signature
    # is emitted under x-only-pubkey || tapleaf-hash, as required by BIP371.
    assert signature_key == plan.expected_pubkey + plan.tapleaf_hash
    output = BytesIO()
    parsed.serialize(output)
    reparsed = psbtObject.read_psbt(BytesIO(output.getvalue()))
    assert signature_key in reparsed.inputs[0].tap_script_sigs
    assert len(reparsed.inputs[0].tap_leaf_scripts) == 1
    assert reparsed.inputs[0].tap_internal_key is not None
    assert reparsed.inputs[0].tap_merkle_root is not None
    reparsed.inputs[0].parse_subpaths(3060347994)
    assert reparsed.inputs[0].tap_subpaths[plan.expected_pubkey][1] == \
        [plan.tapleaf_hash]

    tampered_input = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await tampered_input.validate()
    for path, _ in tampered_input.inputs[0].tap_subpaths.values():
        if path[0] == 3060347994:
            path[-1] = 7
    try:
        tampered_input.consider_inputs()
        assert False, 'Tampered Taproot input was accepted'
    except FatalPSBTIssue:
        pass

    tampered_control = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await tampered_control.validate()
    control, value = next(iter(tampered_control.inputs[0].tap_leaf_scripts.items()))
    del tampered_control.inputs[0].tap_leaf_scripts[control]
    tampered_control.inputs[0].tap_leaf_scripts[
        control[:-1] + bytes([control[-1] ^ 1])] = value
    try:
        tampered_control.consider_inputs()
        assert False, 'Tampered Taproot control block was accepted'
    except FatalPSBTIssue:
        pass

    tampered_change = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await tampered_change.validate()
    tampered_change.consider_inputs()
    tampered_change.outputs[1].parse_subpaths(3060347994)
    for path, _ in tampered_change.outputs[1].tap_subpaths.values():
        if path[0] == 3060347994:
            path[-1] = 8
    try:
        tampered_change.consider_outputs()
        assert False, 'Tampered Taproot change was accepted'
    except FraudulentChangeOutput:
        pass

    # Regression: registered script-path support must not alter Passport's
    # pre-existing BIP86 key-path detection, sighash, or signing branch.
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

    class KeyPathValues(SigningValues):
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
    assert key_input.added_tap_script_sig is None


uasyncio.run(run_test())
