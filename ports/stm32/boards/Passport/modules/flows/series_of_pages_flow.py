# SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# series_of_pages_flow.py - Display a series of pages

from flows import Flow
from foundation import ur


class SeriesOfPagesFlow(Flow):
    def __init__(self, page_class, page_args):
        super().__init__(initial_state=self.display_pages, name='SeriesOfPagesFlow')

        self.page_class = page_class
        self.page_args = page_args

    async def display_pages(self):
        page_index = 0
        result = None
        while page_index < len(self.page_args):
            result = await self.page_class(**self.page_args[page_index]).show()

            if result:
                page_index += 1
            elif page_index > 0:
                page_index -= 1
            else:
                break

        self.set_result(result)
