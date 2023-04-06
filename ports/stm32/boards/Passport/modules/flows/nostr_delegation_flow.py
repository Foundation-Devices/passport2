# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# nostr_delegation_flow.py - Sign a nostr delegation token

from flows import Flow


class NostrDelegationFlow(Flow):
    def __init__(self, context=None):
        from derived_key import get_key_type_from_tn

        self.key = context
        self.key_type = get_key_type_from_tn(self.key['tn'])
        self.nsec = None
        self.npub = None
        self.delegation_string = None
        super().__init__(initial_state=self.export_npub, name='NostrDelegationFlow')

    async def export_npub(self):
        from utils import spinner_task
        from pages import ShowQRPage, ErrorPage

        (vals, error) = await spinner_task(text='Generating npub',
                                                task=self.key_type['task'],
                                                args=[self.key['index']])
        self.nsec = vals['priv']
        self.npub = vals['pub']

        if not self.nsec or not self.npub:
            await ErrorPage("Failed to generate npub and nsec").show()
            self.set_result(False)
            return

        await ShowQRPage(qr_data=self.npub).show()
        self.goto(self.scan_delegation_string)

    async def scan_delegation_string(self):
        from pages import ScanQRPage, ErrorPage

        # TODO: replace with ScanQRFlow
        result = await ScanQRPage().show()

        if not result:
            self.set_result(False)
            return

        if result.is_failure():
            await ErrorPage(text='Unable to scan QR code.').show()
            self.set_result(False)
            return

        self.delegation_string = result.data

        # TODO: parse delegation string, go to display info
        self.set_result(True)
