# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
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
        from common import system, ui, settings
        (fw_version, fw_timestamp, boot_counter, user_signed, fw_date) = system.get_software_info()

        # If there's a beta number, split the string, and convert to decimal
        fw_strings = fw_version.split('b')
        beta_version = ''
        if len(fw_strings) > 1:
            fw_version = fw_strings[0]
            beta_version = " beta {}".format(int(fw_strings[1], 16))

        msg = '''Version {fw_version}{beta_version}
{fw_date}'''.format(fw_version=fw_version, beta_version=beta_version, fw_date=fw_date)

        msg += '''

Boot Counter: {boot_counter}'''.format(boot_counter=boot_counter)

        await SuccessPage(
            msg,
            left_micron=microns.Cancel,
            card_header={'title': 'Current Firmware'}).show()

        self.set_result(True)
