# SPDX-FileCopyrightText: 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

import common
import gc
import uasyncio as asyncio
from display import Display
from keypad import Keypad
from keypad_manager import KeypadManager
from screens import MainScreen
from ui.ui import UI
from pages import ChooserPage, YesNoChooserPage, ShowQRPage
from passport import System


class MockSettings:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value

    def set_volatile(self, key, value):
        pass

    def clear_volatile(self, key):
        pass


common.settings = MockSettings()
common.system = System()
common.display = Display()
common.keypad = Keypad()
common.keypad_manager = KeypadManager()
common.ui = UI(MainScreen())
common.ui.create_single_card(None)


async def run():
    chooser = ChooserPage(card_header={'title': 'Wallet registered'}, options=[
                          {'label': 'Back up wallet policy', 'value': 'backup'}])
    await chooser.display()
    chooser.restore_statusbar_and_card_header()
    backup = YesNoChooserPage(text='How would you like to back up this wallet policy?',
                              yes_text='QR code', no_text='microSD')
    await backup.display()
    backup.restore_statusbar_and_card_header()
    from flows.wallet_policy_flow import ImportWalletPolicyFlow
    from wallet_policy import descriptor_to_policy_template
    from wallet_policy import MiniscriptPolicy
    descriptor = POLICY_DESCRIPTOR
    template, keys = descriptor_to_policy_template(descriptor.strip(), require_checksum=True)
    policy = MiniscriptPolicy('QR test', 'TBTC', template, keys, (0,))
    common.settings.set('wallet_policies', [policy.serialize()])
    flow = ImportWalletPolicyFlow(policy)

    async def close_qr():
        await asyncio.sleep_ms(50)
        page = common.ui.get_active_page()
        assert isinstance(page, ShowQRPage)
        from policy_transport import encode_policy_transport
        gc.collect()
        assert page.qr_data.unwrap_bytes() == encode_policy_transport(policy).encode('utf-8')
        page.update()
        page.set_result(True)
    asyncio.create_task(close_qr())
    await flow.backup_via_qr()
    assert flow.state.__name__ == 'choose_next_action'
    await ChooserPage(options=[{'label': 'Finish', 'value': 'finish'}]).display()
    assert not common.showing_qr
    return_value.write(b'OK')

asyncio.run(run())
