# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# name_device_flow.py - Name or rename the device

from flows import Flow
from serializations import sha256
from pages import TextInputPage, ErrorPage
from common import settings
from constants import MAX_ACCOUNT_NAME_LEN
import microns


class RenameDeviceFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.rename_device, name='NameDeviceFLow')

    async def rename_device(self):
        from utils import spinner_task
        from tasks import delay_task
        from pages import SuccessPage

        name = settings.get('device_name', None) or ''
        result = await TextInputPage(initial_text=name,
                                     max_length=MAX_ACCOUNT_NAME_LEN,
                                     left_micron=microns.Cancel,
                                     right_micron=microns.Checkmark).show()
        if result is None:
            self.set_result(False)
            return

        if len(result) == 0:
            settings.set('device_name', None)
            self.set_result(True)
            return

        prefix = result[:4]
        hashes = [sha256(prefix), sha256(prefix.upper()), sha256(prefix.lower())]
        if settings.get('pin_prefix_hash') in hashes:
            await ErrorPage("Don't use your pin as the device name, because it will be shown on the login page.").show()
            return

        settings.set('device_name', result)

        await spinner_task('Renaming Device', delay_task, args=[1000, False])
        await SuccessPage(text='Device renamed successfully').show()

        self.set_result(True)
