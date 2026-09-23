# SPDX-FileCopyrightText: © 2026 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later

from flows import Flow


class ClearUTXOCacheFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.confirm)

    async def confirm(self):
        from history import OutptValueCache
        from pages import QuestionPage, SuccessPage

        result = await QuestionPage(
            text='Clear remembered transaction input amounts?\n\n'
                 'Only do this to recover from an incorrect UTXO amount error. '
                 'Clearing removes protection against changed amounts in previously signed transactions. '
                 'Verify your transaction details with a trusted wallet before signing again.').show()
        if not result:
            self.set_result(False)
            return

        OutptValueCache.clear()
        await SuccessPage(text='UTXO cache cleared.').show()
        self.set_result(True)
