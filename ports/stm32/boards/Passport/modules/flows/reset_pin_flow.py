# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# reset_pin_flow.py - Change the user's PIN to uninitialized - ONLY FOR DEV

pass
# from flows import Flow
# from pages import PINEntryPage, ErrorPage, SuccessPage
# from tasks import change_pin_task
# from utils import spinner_task
# import microns


# class ResetPINFlow(Flow):
#     def __init__(self):
#         super().__init__(initial_state=self.enter_old_pin, name='ResetPINFlow')

#     async def enter_old_pin(self):
#         (self.old_pin, is_done) = await PINEntryPage(
#             card_header={'title': 'Enter Current PIN'},
#             security_words_message='Remember these Security Words?',
#             left_micron=microns.Back,
#             right_micron=microns.Forward).show()
#         if not is_done:
#             self.set_result(None)
#             return
#         else:
#             self.goto(self.reset_pin)

#     async def reset_pin(self):
#         blank_pin = bytearray([32] * 0)
#         (result, error) = await spinner_task('Resetting PIN...', change_pin_task,
#                                              args=[self.old_pin, blank_pin])
#         if result:
#             self.goto(self.show_success)
#         else:
#             self.error = error
#             self.goto(self.show_error)

#     async def show_success(self):
#         await SuccessPage(text='PIN reset successfully!').show()
#         self.set_result(True)

#     async def show_error(self):
#         await ErrorPage(text='PIN NOT reset: {}'.format(self.error)).show()
#         self.set_result(False)
