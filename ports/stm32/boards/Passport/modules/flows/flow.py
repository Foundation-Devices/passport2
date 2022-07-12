# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# flow.py - Base class for all UI flows

from animations.constants import TRANSITION_DIR_REPLACE, TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
from utils import handle_fatal_error
import common


class Flow():
    def __init__(self, initial_state=None, name='Flow', settings_key=None):
        self.state = initial_state
        self.name = name
        self.prev_states = []
        self.settings_key = settings_key
        self.result = None
        self.done = False

        common.page_transition_dir = TRANSITION_DIR_PUSH

    # Subclasses can call super().get_save_data() first to get a dict, and then add to it and return it
    def get_save_data(self):
        # print('=======================')
        # print('state={}'.format(self.state.__name__))
        # print('=======================')
        return {
            'state': self.state.__name__,
            'name': self.name,
            'prev_states': self.serialize_prev_states(),
            'page_transition_dir': common.page_transition_dir
        }

    def serialize_prev_states(self):
        stack = []
        for entry in self.prev_states:
            stack.append(entry.__name__)
        # print('serialized stack={}'.format(stack))
        return stack

    def deserialize_prev_states(self, saved_stack):
        stack = []
        for state_function_name in saved_stack:
            # print('lookup "{}"'.format(state_function_name))
            stack.append(getattr(self, state_function_name))

        # print('deserialized stack={}'.format(stack))
        return stack

    def save(self):
        if self.settings_key is not None:
            save_data = self.get_save_data()
            common.settings.set(self.settings_key, save_data)

    def restore_items(self, data):
        # print('restore_items = {}'.format(data))
        common.page_transition_dir = data.get('page_transition_dir', TRANSITION_DIR_PUSH)
        self.prev_states = self.deserialize_prev_states(data.get('prev_states', []))
        self.state = getattr(self, data.get('state'))

    def erase_settings(self):
        if self.settings_key is not None:
            common.settings.remove(self.settings_key)

    def restore(self):
        if self.settings_key is not None:
            data = common.settings.get(self.settings_key, None)
            if data is not None:
                self.restore_items(data)

    def cleanup(self):
        import gc
        gc.collect()
        # from utils import mem_info
        # mem_info(label='{}.cleanup(): '.format(self.name), map=False)

    def goto(self, new_state, save_curr=True):
        if save_curr:
            self.prev_states.append(self.state)
        common.page_transition_dir = TRANSITION_DIR_PUSH
        self.state = new_state

        # Auto-save
        self.save()
        self.cleanup()

    # Reset the state machine with no prev_states, starting at the specified state
    def reset(self, new_state):
        self.prev_states = []
        self.goto(new_state, save_curr=False)

        # Auto-save
        self.save()
        self.cleanup()

    def back(self):
        # print('back() len={}'.format(len(self.prev_states)))
        if len(self.prev_states) > 0:
            prev_state = self.prev_states.pop()
            # print('{}: Go BACK from {} to {}'.format(self.name, self.state, prev_state))
            self.state = prev_state
            common.page_transition_dir = TRANSITION_DIR_POP

            # Auto-save
            self.save()
            self.cleanup()
            return True  # Was able to go back
        else:
            common.page_transition_dir = TRANSITION_DIR_REPLACE
            self.cleanup()
            return False  # Was NOT able to go back, which means we are probably exiting the flow

    async def wait_to_die(self):
        from uasyncio import sleep_ms
        # This task just started an operation that will cede control to another card_task,
        # and if we were to keep going, there would be a race condition for control of the UI
        # between this card_task and the new one, so we just wait here.  The old card_task
        # (the one calling wait_to_die()) should be killed usually within the next second.
        await sleep_ms(10000)

    def set_result(self, result, forget_state=True):
        common.page_transition_dir = TRANSITION_DIR_POP
        self.result = result
        self.done = True

        # When result is set, we can forget the saved flow state, unless caller wants
        # to keep it explicitly.
        if forget_state:
            self.erase_settings()

    async def run(self):
        try:
            while not self.done:
                await self.state()

            return self.result
        except Exception as e:
            handle_fatal_error(e)
