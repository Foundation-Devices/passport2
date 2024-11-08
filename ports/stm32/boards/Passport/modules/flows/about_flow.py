# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# about_flow.py - About Passport, and regulatory info

import lvgl as lv
from flows import Flow
from pages import LongTextPage
from utils import xfp2str, swab32, recolor
import microns
from styles.colors import HIGHLIGHT_TEXT_HEX, TEXT_GREY


class AboutFlow(Flow):
    def __init__(self):
        super().__init__(initial_state=self.about_page, name='AboutFlow')

    async def about_page(self):
        from common import settings, system
        from utils import has_seed

        serial = system.get_serial_number()
        my_xfp = settings.get('xfp', 0)
        xpub = settings.get('xpub', None)

        if has_seed():
            msg = '''
{xfp_title}
{xfp}

{rev_xfp_title}
{rev_xfp}

{xpub_title}
{xpub}
'''.format(
                xfp_title=recolor(HIGHLIGHT_TEXT_HEX, 'Master Fingerprint'),
                xfp=xfp2str(my_xfp) if my_xfp else '<No Seed Yet>',
                rev_xfp_title=recolor(HIGHLIGHT_TEXT_HEX, 'Reversed Fingerprint'),
                rev_xfp=xfp2str(swab32(my_xfp)) if my_xfp else '<No Seed Yet>',
                xpub_title=recolor(HIGHLIGHT_TEXT_HEX, 'Master XPUB'),
                xpub=xpub if xpub is not None else '<No Seed Yet>')
        else:
            msg = ''

        msg += '''
{serial_title}
{serial}'''.format(
            serial_title=recolor(HIGHLIGHT_TEXT_HEX, 'Serial Number'),
            serial=serial)

        # print('msg={}'.format(msg))

        result = await LongTextPage(text=msg, centered=True).show()
        if result:
            self.goto(self.regulatory_page)
        else:
            self.set_result(False)

    async def regulatory_page(self):
        from common import ui

        msg = """
{title}

Foundation Devices
6 Liberty Square ##6018
Boston, MA 02109 USA""".format(title=recolor(HIGHLIGHT_TEXT_HEX, 'PASSPORT'))
        result = await LongTextPage(
            text=msg,
            icon=lv.IMAGE_REGULATORY,
            icon_color=TEXT_GREY,
            centered=True,
            card_header={'title': 'Regulatory'},
            right_micron=microns.Checkmark).show()

        if result:
            self.set_result(False)
            return
        self.goto(self.about_page)
