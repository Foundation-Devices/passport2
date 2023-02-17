# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# scan_qr_seed_flow.py - Scan a QR code containing a seed

from flows import Flow
from pages import ErrorPage, QuestionPage, SuccessPage
from tasks import new_seed_task, save_seed_task
from utils import has_secrets, spinner_task
from translations import t, T


class ScanQRSeedFlow(Flow):
    def __init__(self, refresh_cards_when_done=False, autobackup=True, full_backup=False):
        super().__init__(initial_state=self.confirm_scan, name='ScanQRSeedFlow')
        self.refresh_cards_when_done = refresh_cards_when_done
        self.autobackup = autobackup
        self.full_backup = full_backup

    async def confirm_scan(self):
        # Ensure we don't overwrite an existing seed
        if has_secrets():
            await ErrorPage(text='Passport already has a seed!').show()
            self.set_result(False)
            return

        result = await QuestionPage(text='Scan a QR seed now? Make sure you trust the source.').show()
        if result:
            self.goto(self.scan_seed)
        else:
            self.set_result(False)

    async def scan_seed(self):
        from pages import ScanQRPage, ErrorPage
        from ubinascii import unhexlify as a2b_hex

        result = await ScanQRPage().show()

        if result is None:
            self.set_result(False)
            return

        try:
            seed = a2b_hex(result.data)
        except Exception as e:
            self.error = "Not a valid seed"
            self.goto(self.show_error)
            return

        if len(seed) > 32:
            self.error = "Seed too long"
            self.goto(self.show_error)
            return

        self.seed = seed
        self.goto(self.save_seed)

    async def save_seed(self):
        (error,) = await spinner_task('Saving Seed', save_seed_task, args=[self.seed])
        if error is None:
            self.goto(self.show_seed_words)
        else:
            self.error = 'Unable to save seed.'
            self.goto(self.show_error)

    async def show_seed_words(self):
        from flows import ViewSeedWordsFlow
        await ViewSeedWordsFlow().run()
        self.goto(self.show_success)

    async def show_success(self):
        import common
        from flows import AutoBackupFlow, BackupFlow

        await SuccessPage(text='New seed saved.').show()
        if self.full_backup:
            await BackupFlow().run()
        elif self.autobackup:
            await AutoBackupFlow(offer=True).run()

        if self.refresh_cards_when_done:
            common.ui.full_cards_refresh()

            await self.wait_to_die()
        else:
            self.set_result(True)

    async def show_error(self):
        await ErrorPage(self.error).show()
        self.set_result(False)
