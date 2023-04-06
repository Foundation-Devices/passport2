# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# menu_flow.py - Flow class to track position in a menu

from animations.constants import TRANSITION_DIR_POP, TRANSITION_DIR_PUSH
from flows import Flow, PageFlow
from pages import MenuPage, ShutdownPage
import microns
import common


class MenuFlow(Flow):
    latest_menu = None

    def __init__(self, menu, initial_selected_index=0, is_top_level=None, context=None,
                 card_header=None, statusbar=None, dynamic=None):
        self.menu = menu

        super().__init__(initial_state=self.show_menu, name='MenuFlow')
        self.selected_index = initial_selected_index
        self.selected_item = None
        self.is_top_level = is_top_level
        self.context = context
        self.card_header = card_header
        self.statusbar = statusbar
        self.dynamic = dynamic
        MenuFlow.latest_menu = self

    async def show_menu(self):
        from common import ui
        self.cleanup()

        # Regenerate the menu items each time if this is a function.
        # This allows them to update if any state has changed since last running.
        assert(callable(self.menu))
        self.items = self.menu()
        if self.dynamic:
            assert(callable(self.dynamic))
            self.items.extend(self.dynamic())
        self.prev_statusbar = None
        self.prev_card_header = None

        # print('show_menu(): is_top_level() = {}'.format(common.ui.is_top_level()))
        result = await MenuPage(
            self.items,
            self.selected_index,
            # left_micron=microns.Back if not common.ui.is_top_level() else microns.Shutdown,
            card_header=self.card_header,
            statusbar=self.statusbar,
            left_micron=microns.Back,
            right_micron=microns.Checkmark,
            is_top_level=self.is_top_level
        ).show()
        if result is None:
            if ui.is_top_level():
                await ShutdownPage().show()
            else:
                common.page_transition_dir = TRANSITION_DIR_POP
                self.set_result(None)

            self.cleanup()
        else:
            self.selected_index, self.selected_item = result
            common.page_transition_dir = TRANSITION_DIR_PUSH
            item = self.selected_item

            if item.get('submenu') is not None:
                # TODO: this and the flow case have a lot in common
                # If it contains a submenu, then just call MenuFlow recursively
                auto = item.get('auto_card_header', True)
                self.update_headers(item, auto)
                args = item.get('args', {})
                if self.context is not None:
                    args['context'] = self.context

                # print('MENUFLOW >>>>>>> args={}'.format(args))
                submenu = item.get('submenu')
                result = await MenuFlow(submenu, **args).run()
                self.revert_headers(auto)

                if result and item.get('exit_on_success', False):
                    # User picked this item, which invalidates this menu
                    self.set_result(True)

                # Trigger a card refresh, usually because an Extension was enabled or disabled
                if self.is_top_level and ui.update_cards_pending:
                    ui.update_cards(stay_on_same_card=True)

            elif item.get('page') is not None:
                # If there is a page, present it with the simple PageFlow
                args = self.apply_page_args(item)

                # prev_card_header = self.update_card_header(item)
                # print('PAGE >>>>>>> args={}'.format(args))
                result = await PageFlow(args).run()
                # if prev_card_header is not None:
                #     ui.set_card_header(**prev_card_header)

                if result and item.get('exit_on_success', False):
                    # User picked this item, which invalidates this menu
                    self.set_result(True)

            elif item.get('flow') is not None:

                # If there is a flow, run it
                flow = item.get('flow')

                auto = item.get('auto_card_header', True)
                self.update_headers(item, auto)
                args = item.get('args', {})
                if self.context is not None:
                    args['context'] = self.context
                # print('FLOW >>>>>>> args={}'.format(args))
                result = await flow(**args).run()

                self.revert_headers(auto)

                if result and item.get('exit_on_success', False):
                    # User picked this item, which invalidates this menu
                    self.set_result(True)

            elif item.get('action') is not None:
                action = item.get('action')
                if callable(action):
                    action(item)

            self.cleanup()

    def apply_page_args(self, item):
        args = item.get('args', {})

        # This is needed by PageFlow to know what page class to instantiate
        args['page_class'] = item.get('page')
        if self.context is not None:
            args['context'] = self.context

        # Add the auto card_header unless  is False or there is already a card_header
        card_header = item.get('card_header', None)
        if card_header is not None:
            # card_title = card_header.get('title', None)
            # if card_title is not None:
            #     item.set('title', card_title)

            # card_icon = card_header.get('icon', None)
            # if card_icon is not None:
            #     item.set('icon', card_icon)
            # else:
            #     # Default to the icon from the menu item
            #     item.set('icon', item.get('icon', None))
            pass
        else:
            card_header = {'title': item.get('label'), 'icon': item.get('icon')}

        args['card_header'] = card_header

        return args

    def update_card_header(self, item):
        from common import ui

        # Add the auto card_header unless auto_card_header is False or there is already a card_header
        card_header = item.get('card_header', None)
        if card_header is not None:
            card_title = card_header.get('title', None)
            card_icon = card_header.get('icon', None)
            card_right_icon = card_header.get('right_icon', None)

            return ui.set_card_header(title=card_title, icon=card_icon, right_icon=card_right_icon)

        return ui.get_card_header()

    # Automatically assign screen header to menu label and icon unless
    # auto_screen_header is present and False.
    def update_statusbar(self, item):
        from common import ui

        statusbar = item.get('statusbar', None)
        if statusbar is not None:
            statusbar_title = statusbar.get('title', None)
            statusbar_icon = statusbar.get('icon', None)
        else:
            statusbar_title = item.get('label', '').upper()
            statusbar_icon = item.get('icon', None)

        if statusbar_title is not None or statusbar_icon is not None:
            return ui.set_statusbar(title=statusbar_title, icon=statusbar_icon)

        return None

    def update_prev_statusbar(self, statusbar):
        self.prev_statusbar = statusbar

    def get_prev_statusbar(self):
        return self.prev_statusbar

    def update_prev_card_header(self, card_header):
        self.prev_card_header = card_header

    def get_prev_card_header(self):
        return self.prev_card_header

    def revert_headers(self, auto=True):
        from common import ui
        if self.prev_statusbar is not None:
            ui.set_statusbar(**self.prev_statusbar)
            self.prev_statusbar = None

        if not auto and self.prev_card_header is not None:
            ui.set_card_header(**self.prev_card_header)
            self.prev_card_header = None

    def update_headers(self, item, auto=True):
        from common import ui

        self.prev_statusbar = self.update_statusbar(item)
        if not auto:
            self.prev_card_header = self.update_card_header(item)
        else:
            self.prev_card_header = ui.get_card_header()
