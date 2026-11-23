# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Onboarding no longer runs the Security Check. Progress saved by older firmware can still name its stage,
# and must restore instead of starting onboarding again.

import uasyncio as asyncio

import common
import flows
import pages
from animations.constants import TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
from flows import EnvoySetupFlow, ManualSetupFlow


class MemorySettings:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)


class MockSystem:
    def get_software_info(self):
        return ('v2.4.0', None, None, None, None)


class MockPage:
    def __init__(self, **kwargs):
        pass

    async def show(self):
        return True


class MockFlow:
    def __init__(self, **kwargs):
        pass

    async def run(self):
        return True


def saved(state, prev_states, page_transition_dir=TRANSITION_DIR_PUSH):
    return {'state': state, 'name': 'saved', 'prev_states': prev_states, 'page_transition_dir': page_transition_dir}


def state_name(flow):
    return flow.state.__name__


def prev_state_names(flow):
    return [state.__name__ for state in flow.prev_states]


async def run_tests():
    # New onboarding goes straight to the PIN.
    common.settings = MemorySettings()
    flow = EnvoySetupFlow()
    await flow.show_envoy_app_url()
    assert state_name(flow) == 'set_initial_pin'

    common.settings = MemorySettings()
    flow = ManualSetupFlow()
    await flow.show_terms_of_use_flow()
    assert state_name(flow) == 'set_initial_pin'

    # Progress saved after the Security Check restores, and going back passes over its stage.
    envoy_progress = saved('setup_seed', ['show_envoy_app_url', 'scv_flow', 'set_initial_pin', 'update_firmware'])
    common.settings = MemorySettings({'envoy_setup': envoy_progress})
    flow = EnvoySetupFlow()
    assert state_name(flow) == 'setup_seed'
    assert common.settings.get('envoy_setup') is not None
    flow.back()
    flow.back()
    assert state_name(flow) == 'set_initial_pin'
    flow.back()
    await flow.state()
    assert state_name(flow) == 'show_envoy_app_url'
    assert flow.prev_states == []

    manual_progress = saved('set_initial_pin',
                            ['show_intro', 'show_setup_guide_url', 'show_terms_of_use_flow', 'show_scv'])
    common.settings = MemorySettings({'manual_setup': manual_progress})
    flow = ManualSetupFlow()
    assert state_name(flow) == 'set_initial_pin'
    flow.back()
    await flow.state()
    assert state_name(flow) == 'show_terms_of_use_flow'
    assert prev_state_names(flow) == ['show_intro', 'show_setup_guide_url']

    # Progress saved during the Security Check continues to the PIN, and going back skips the stage.
    common.settings = MemorySettings({'envoy_setup': saved('scv_flow', ['show_envoy_app_url'])})
    flow = EnvoySetupFlow()
    await flow.state()
    assert state_name(flow) == 'set_initial_pin'
    assert prev_state_names(flow) == ['show_envoy_app_url']

    common.settings = MemorySettings({'manual_setup': saved(
        'show_scv', ['show_intro', 'show_setup_guide_url', 'show_terms_of_use_flow'])})
    flow = ManualSetupFlow()
    await flow.state()
    assert state_name(flow) == 'set_initial_pin'
    assert prev_state_names(flow) == ['show_intro', 'show_setup_guide_url', 'show_terms_of_use_flow']

    # The saved direction decides which way to pass through.
    common.settings = MemorySettings({'envoy_setup': saved('scv_flow', ['show_envoy_app_url'], TRANSITION_DIR_POP)})
    flow = EnvoySetupFlow()
    await flow.state()
    assert state_name(flow) == 'show_envoy_app_url'


original_settings = common.settings
original_system = common.system
original_show_qr_page = pages.ShowQRPage
original_terms_of_use_flow = flows.TermsOfUseFlow
common.system = MockSystem()
pages.ShowQRPage = MockPage
flows.TermsOfUseFlow = MockFlow
try:
    asyncio.run(run_tests())
    return_value.write(b'OK')
finally:
    common.settings = original_settings
    common.system = original_system
    pages.ShowQRPage = original_show_qr_page
    flows.TermsOfUseFlow = original_terms_of_use_flow
