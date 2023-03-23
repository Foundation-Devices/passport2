# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_current_firmware_flow.py - View the current firmware information

from flows import Flow
from pages import SuccessPage
import microns


class ViewCurrentFirmwareFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_info, name='ViewCurrentFirmwareFlow')

    async def show_info(self):
        from common import system, ui
        (fw_version, fw_timestamp, boot_counter, user_signed, fw_date) = system.get_software_info()

        msg = '''Version {fw_version}
{fw_date}'''.format(fw_version=fw_version, fw_date=fw_date)

        # if user_signed:
        #     msg += '\nSigned by User'

        msg += '''

Boot Counter: {boot_counter}'''.format(boot_counter=boot_counter)

        await SuccessPage(
            msg,
            left_micron=microns.Cancel,
            card_header={'title': 'Current Firmware'}).show()

        self.set_result(True)
