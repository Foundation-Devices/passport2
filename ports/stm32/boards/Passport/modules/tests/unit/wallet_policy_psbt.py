# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

"""MicroPython integration smoke test for registered P2WSH policy matching."""

import uasyncio
from ubinascii import a2b_base64, unhexlify
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


LIANA_DESCRIPTOR = (

)

LIANA_PSBT_BASE64 = (
    "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"
    "AAAAAQAAAAA=wsh(or_i(and_v(v:thresh(2,pkh([9f141cf0/48'/1'/0'/2']tpubDFnReAwXvYd6RA46X55HuFpmvZsLanD"
    "rwHAUsdYEGEpNGTRnCdbDRXJGLTwDeqKURCPZUDgdkuuu9dYkuBNQHmSNBUu7V2CdLKwpJjx2JuC/<2;3>/*),a:pkh([daba2d5"
    "f/48'/1'/0'/2']tpubDDwKEc4i4k8rBgVLGxytHrP13VVYucUGmL2cadux7AfMwMnRHKcw1YZKt9SMB4fWut7ZAiZqPefzm3BBC"
    "NXLZMxDrWJ4Q6VA1AFB6b8GzbT/<2;3>/*),a:pkh([141cfdf4/48'/1'/0'/2']tpubDEnYysximqdZkZnW5W9gYc7N3sxizKy"
    "qfdJfZ2qRfwNvSv6E11yDgyLTAnWQqDmVJ7oQ3h3ui59RQm1qmGxMm4jinq5wvSzyueKgrLJj5Cy/<0;1>/*)),older(52596))"
    ",and_v(v:pk([9f141cf0/48'/1'/0'/2']tpubDFnReAwXvYd6RA46X55HuFpmvZsLanDrwHAUsdYEGEpNGTRnCdbDRXJGLTwDe"
    "qKURCPZUDgdkuuu9dYkuBNQHmSNBUu7V2CdLKwpJjx2JuC/<0;1>/*),pk([daba2d5f/48'/1'/0'/2']tpubDDwKEc4i4k8rBg"
    "VLGxytHrP13VVYucUGmL2cadux7AfMwMnRHKcw1YZKt9SMB4fWut7ZAiZqPefzm3BBCNXLZMxDrWJ4Q6VA1AFB6b8GzbT/<0;1>/"
    "*))))#u768v50p"
)


async def run_liana_multipath_change_test():
    policy = MiniscriptPolicy.from_multipath_descriptor(
        'Liana Multisig', 'TBTC', LIANA_DESCRIPTOR, (0,))
    my_xfp = int.from_bytes(unhexlify('9f141cf0'), 'little')
    common.settings.set('chain', 'TBTC')
    common.settings.set('xfp', my_xfp)
    common.settings.set('wallet_policies', [policy.serialize()])

    parsed = psbtObject.read_psbt(BytesIO(a2b_base64(LIANA_PSBT_BASE64)))
    await parsed.validate()
    parsed.consider_inputs()
    parsed.consider_keys()
    parsed.consider_outputs()

    assert parsed.active_policy.policy_id == policy.policy_id
    assert parsed.calculate_fee() == 3220
    assert not parsed.outputs[0].is_change
    assert parsed.outputs[1].is_change
    assert parsed.outputs[1].policy_branch == 1
    assert parsed.outputs[1].policy_address_index == 1
    assert not any(title == 'Suspicious Change Outputs'
                   for title, _ in parsed.warnings)


async def run_all():
    await run_test()
    await run_liana_multipath_change_test()


uasyncio.run(run_all())
