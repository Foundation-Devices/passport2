# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from flows import Flow


class ClearUTXOCacheFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm)

    async def confirm(self):
        from history import OutptValueCache
        from pages import LongQuestionPage, SuccessPage

        result = await LongQuestionPage(
            text='Clear saved input amounts?\n\n'
                 "Only use this if Passport rejected a transaction because an input amount didn't match.\n\n"
                 'Passport will forget amounts from past signings, '
                 'so check the amounts in a trusted wallet before you sign again.').show()
        if not result:
            self.set_result(False)
            return

        OutptValueCache.clear()
        await SuccessPage(text='UTXO cache cleared.').show()
        self.set_result(True)
