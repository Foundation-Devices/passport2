# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view_dev_pubkey_flow.py - Flow to show the developer pubkey to the user

from flows import Flow
from pages import StatusPage
import microns
from utils import read_user_firmware_pubkey, bytes_to_hex_str, split_to_lines


class ViewDevPubkeyFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.show_dev_pubkey)

    async def show_dev_pubkey(self):
        pubkey_result, pubkey = read_user_firmware_pubkey()
        if pubkey_result:
            pubkey = bytes_to_hex_str(pubkey)
            pubkey = split_to_lines(pubkey, 16)
        else:
            pubkey = 'Unable to read Developer PubKey'

        await StatusPage(
            card_header={'title': 'Installed PubKey'},
            statusbar={'title': 'DEVELOPER'},
            text=pubkey,
            centered=True,
            left_micron=microns.Back,
            right_micron=microns.Checkmark
        ).show()
        self.set_result(True)
