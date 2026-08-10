# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""MicroPython integration smoke test for registered P2WSH policy matching."""

import uasyncio
from ubinascii import a2b_base64
from uio import BytesIO

import common
import history
from exceptions import FatalPSBTIssue, FraudulentChangeOutput
from psbt import psbtObject
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
    "[4ba43603/84'/0'/0']"
    'xpub6CFtfy4QXsEUW5CtgE7mZe1Lvs15Yw7ctjdyaDRy89JdhtyM1wFf8uY2BdyJ3JmAFfrHdw77hEit1ebVXxB2dytGAvq9mmQJ2c83G1q8P7A'
)
FOREIGN_KEY = (
    "[8dfc9b34/84'/0'/0']"
    'xpub6DCej1mg88MtuioUhGkKje5aJMMFbUswXEcrqt46xGCtwy48Q6D5YaFrhWykLp4ZeqM6XpeXxWuudr7EZkmMT4abxjZRMEhFRBw4SRmjTzY'
)
PSBT_BASE64 = (
    'cHNidP8BAH0CAAAAARERERERERERERERERERERERERERERERERERERERERERAAAAAAD+////AkCcAAAAAAAAFgAU+VKOB0Yx'
    'CX/JIFOUnH4pv76pmxt45gAAAAAAACIAIBQNx0qU+iLrkj8cwktB0/JDXPxgHaxHJwQE4AX2biNHAAAAAAABASughgEAAAAA'
    'ACIAIL1vQENUdKouleK1JZzGQSakjVf6Edv+C09oOEzkGPG7AQVLIQIE4W+zgtYA9gyHBVoH0QTwDeJv4cIajiUN0zWuRHEp'
    'RqxzZCEDSfcwW2+LRqxR53wkQyso0V56ZmcmEN1Bu9w0JUgxjnmtWrJoIgYCBOFvs4LWAPYMhwVaB9EE8A3ib+HCGo4lDdM1'
    'rkRxKUYYS6Q2A1QAAIAAAACAAAAAgAAAAAAFAAAAIgYDSfcwW2+LRqxR53wkQyso0V56ZmcmEN1Bu9w0JUgxjnkYjfybNFQA'
    'AIAAAACAAAAAgAAAAAAFAAAAAAABAUshApWOxM8od+Dx3R9ioG/Vi/Iebvd7cMCz/x1xixzhgZj6rHNkIQPVlFife7kL+nve'
    'D8adbK1Lq/DMwLoDlx/GFT0kj8ql/q1asmgiAgKVjsTPKHfg8d0fYqBv1YvyHm73e3DAs/8dcYsc4YGY+hhLpDYDVAAAgAAA'
    'AIAAAACAAQAAAAYAAAAiAgPVlFife7kL+nveD8adbK1Lq/DMwLoDlx/GFT0kj8ql/hiN/Js0VAAAgAAAAIAAAACAAQAAAAYA'
    'AAAA'
)


async def run_test():
    policy = MiniscriptPolicy(
        'Recovery', 'BTC',
        'wsh(or_d(pk(@0/**),and_v(v:pk(@1/**),older(10))))',
        (OWNED_KEY, FOREIGN_KEY), (0,))
    common.settings.set('chain', 'BTC')
    common.settings.set('xfp', 53912651)
    common.settings.set('wallet_policies', [policy.serialize()])

    parsed = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await parsed.validate()
    history.verify_amount = lambda *args: None
    parsed.consider_inputs()
    parsed.consider_keys()
    parsed.consider_outputs()

    assert parsed.active_policy.policy_id == policy.policy_id
    plan = parsed.inputs[0].policy_spend_plan
    assert plan.policy_id == policy.policy_id
    assert plan.branch == 0 and plan.address_index == 5
    assert parsed.inputs[0].required_key == {plan.expected_pubkey}
    assert parsed.outputs[1].is_change
    assert parsed.outputs[1].policy_branch == 1
    assert parsed.outputs[1].policy_address_index == 6

    # Liana includes complete output derivations but may omit the change
    # output's witness script.  The registered policy must reconstruct and
    # verify it rather than rejecting an otherwise complete PSBT.
    omitted_output_script = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await omitted_output_script.validate()
    omitted_output_script.consider_inputs()
    omitted_output_script.outputs[1].witness_script = None
    omitted_output_script.consider_outputs()
    assert omitted_output_script.outputs[1].is_change
    assert omitted_output_script.outputs[1].policy_branch == 1
    assert omitted_output_script.outputs[1].policy_address_index == 6

    # An altered input derivation must fail policy matching before signing.
    tampered_input = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await tampered_input.validate()
    for path in tampered_input.inputs[0].subpaths.values():
        if path[0] == 53912651:
            path[-1] = 7
    try:
        tampered_input.consider_inputs()
        assert False, 'Tampered policy input was accepted'
    except FatalPSBTIssue:
        pass

    # Input matching can succeed while independently altered change metadata
    # must still be rejected as fraudulent change.
    tampered_change = psbtObject.read_psbt(BytesIO(a2b_base64(PSBT_BASE64)))
    await tampered_change.validate()
    tampered_change.consider_inputs()
    tampered_change.outputs[1].parse_subpaths(53912651)
    for path in tampered_change.outputs[1].subpaths.values():
        if path[0] == 53912651:
            path[-1] = 8
    try:
        tampered_change.consider_outputs()
        assert False, 'Tampered policy change was accepted'
    except FraudulentChangeOutput:
        pass


uasyncio.run(run_test())
