# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# page_flow.py - Flow class to present a single Page that doesn't forward to other pages (e.g., a settings Page)

from flows.flow import Flow


class PageFlow(Flow):
    def __init__(self, args):
        super().__init__(initial_state=self.show_page, name='PageFlow')
        self.page_class = args.get('page_class')
        page_args = args.copy()
        del page_args['page_class']
        self.args = page_args

    async def show_page(self):
        result = await self.page_class(**self.args).show()
        self.set_result(result)
