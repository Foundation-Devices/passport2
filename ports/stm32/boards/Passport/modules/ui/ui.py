# SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# ui.py - High-level UI interface

import lvgl as lv
import common


def get_account_bg(account):
    from styles.colors import ACCOUNT_COLORS
    return ACCOUNT_COLORS[account.get('acct_num') % len(ACCOUNT_COLORS)].get('bg')


def get_account_fg(account):
    from styles.colors import ACCOUNT_COLORS
    return ACCOUNT_COLORS[account.get('acct_num') % len(ACCOUNT_COLORS)].get('fg')


class UI():
    def __init__(self, initial_screen=None):
        self.active_screen = initial_screen
        self.group = lv.group_create()
        self.card_descs = []
        self.active_card_idx = None
        self.active_card_task = None
        self.active_account = None
        self._is_top_level = True
        self.battery_level = 100

        common.keypad_indev.set_group(self.group)
        self.render(None, self.active_screen)

    def set_screen(self, new_screen):
        self.render(self.active_screen, new_screen)

    def render(self, old_screen, new_screen):
        try:
            # Detach and unmount any currently active screen
            if old_screen:
                old_screen.detach(self.group)
                old_screen.unmount(None)

                old_screen_widget = lv.scr_act()
                if old_screen_widget is not None:
                    old_screen_widget.delete()

            # Mount and attach the new screen, then tell lvgl about it
            new_screen_widget = new_screen.mount(None)
            new_screen.attach(self.group)
            lv.scr_load(new_screen_widget)

        except Exception as e:
            import sys
            print('==============================================================================================\n\n')
            print('Exception in ui.render(): {}\n\n'.format(e))
            print('==============================================================================================')
            sys.print_exception(e)

    # Set the theme to color or mono in light or dark mode
    def set_theme(self, theme_name, is_dark_mode):
        from styles.colors import WHITE, MEDIUM_GREY
        if theme_name == 'color':
            curr_theme = lv.theme_get_from_obj(lv.scr_act())
            new_theme = lv.theme_default_init(
                lv.disp_get_default(),
                WHITE,
                MEDIUM_GREY,
                is_dark_mode,
                curr_theme.font_small)
        elif theme_name == 'mono':
            curr_theme = lv.theme_get_from_obj(lv.scr_act())
            try:
                new_theme = lv.theme_mono_init(lv.disp_get_default(), is_dark_mode, curr_theme.font_small)
            except Exception as e:
                # print('e={}'.format(e))
                pass

        lv.disp_get_default().set_theme(new_theme)

    def set_left_pressed(self, is_pressed):
        self.active_screen.card_nav.micron_bar.set_left_pressed(is_pressed)

    def set_right_pressed(self, is_pressed):
        self.active_screen.card_nav.micron_bar.set_right_pressed(is_pressed)

    def set_left_micron(self, micron):
        self.active_screen.card_nav.micron_bar.set_left_micron(micron)

    def set_right_micron(self, micron):
        self.active_screen.card_nav.micron_bar.set_right_micron(micron)

    # Returns a dict of the previous title and icon
    def set_statusbar(self, title=None, icon=None, fg_color=None):
        return self.active_screen.set_statusbar(title=title, icon=icon, fg_color=fg_color)

    def set_screen_bg_color(self, bg_color):
        self.active_screen.set_bg_color(bg_color)

    def set_cards(self, card_descs, active_idx=0):
        assert(active_idx >= 0)
        assert(active_idx < len(card_descs))

        # print('set_cards: len={}'.format(len(card_descs)))
        self.card_descs = card_descs
        self.active_card_idx = active_idx
        active_card_desc = self.card_descs[self.active_card_idx]
        self.active_screen.card_nav.set_cards(self.card_descs, self.active_card_idx)
        self.active_screen.card_nav.replace_card(active_card_desc)
        self.update_screen_info(active_card_desc)

    # Really just setting the dots
    def set_micron_bar_cards(self, card_descs, force_show=True):
        return self.active_screen.card_nav.micron_bar.set_cards(card_descs, force_show=force_show)

    def set_micron_bar_active_idx(self, active_idx):
        return self.active_screen.card_nav.micron_bar.set_active_idx(active_idx)

    def get_active_card(self):
        return self.active_screen.card_nav.active_card

    def get_active_page(self):
        return self.get_active_card().page

    def get_card_header(self):
        card = self.get_active_card()
        assert(card is not None)
        return card.get_header()

    def set_card_header(
            self, title=None, icon=None, right_icon=None, right_text=None, bg_color=None, fg_color=None,
            force_all=False):
        card = self.get_active_card()
        prev_header = card.get_header()
        assert(card is not None)
        card.set_header(title=title, icon=icon, right_icon=right_icon, right_text=right_text,
                        bg_color=bg_color, fg_color=fg_color, force_all=force_all)
        return prev_header

    def hide_card_header(self):
        return self.set_card_header(title=None)

    def create_single_card(self, flow, card=None, args=None, add_settings=False):
        from styles.colors import LIGHT_GREY, TEXT_GREY, WHITE, LIGHT_TEXT
        import microns

        # Add the leftmost settings card
        if card is None:
            card = {
                'header_color': LIGHT_GREY,
                'header_fg_color': LIGHT_TEXT,
                'statusbar': {'title': 'PASSPORT', 'icon': lv.ICON_HAMBURGER, 'fg_color': WHITE},
                'page_micron': microns.PageDot,
                'bg_color': TEXT_GREY,
                'flow': flow
            }

        if args is not None:
            card['args'] = args

        card_descs = []
        active_idx = 0

        # Add the settings card if requests (e.g., during onboarding flow)
        # It will be restricted to only the valid operations based on the state of being logged in,
        # whether a seed exists, etc.
        if add_settings:
            settings_card = self.make_settings_card()
            card_descs.append(settings_card)
            active_idx += 1

        card_descs.append(card)
        self.set_cards(card_descs, active_idx=active_idx)
        return len(card_descs)

    def make_settings_card(self):
        from flows import MenuFlow
        from menus import settings_menu
        import microns
        from styles.colors import LIGHT_GREY, TEXT_GREY, WHITE, LIGHT_TEXT

        return {
            'header_color': LIGHT_GREY,
            'header_fg_color': LIGHT_TEXT,
            'statusbar': {'title': 'SETTINGS', 'icon': lv.ICON_HAMBURGER, 'fg_color': WHITE},
            'page_micron': microns.PageHome,
            'bg_color': TEXT_GREY,
            'flow': MenuFlow,
            'args': {'menu': settings_menu, 'is_top_level': True}
        }

    def update_cards_on_top_level(self):
        # print('Setting update_cards_pending to True')
        self.update_cards_pending = True

    def update_cards(
            self, is_delete_account=False, stay_on_same_card=False, is_new_account=False, is_init=False):
        from flows import MenuFlow
        from utils import get_accounts, has_seed
        from menus import account_menu, plus_menu
        from extensions.extensions import supported_extensions
        from constants import MAX_ACCOUNTS
        from styles.colors import DARK_GREY, LIGHT_GREY, LIGHT_TEXT, WHITE
        import microns

        self.update_cards_pending = False

        # Add the leftmost settings card
        settings_card = self.make_settings_card()
        card_descs = [settings_card]

        # Add the account cards
        accounts = get_accounts()
        accounts = accounts[:MAX_ACCOUNTS]

        new_card_idx = None

        # print('len(self.card_descs)={}  len(accounts)={}'.format(len(self.card_descs), len(accounts)))

        # See if we are adding or removing or staying the same
        if is_init:
            pass
            # First time, so we go to the first account (we always have Primary)
            # new_card_idx = 1
        elif is_delete_account:
            # User removed a card, which is done from the account card page
            # So we can leave active_card_idx unchanged unless that would move
            # to a non-account page (we have to stay in the same card task flow)
            new_card_idx = self.active_card_idx
            if new_card_idx == len(accounts) + 1:
                new_card_idx -= 1
        elif is_new_account:
            # User added a new account, which is done from the last card, so
            # let's ensure we are still on the last page.
            new_card_idx = self.active_card_idx + 1
        elif stay_on_same_card:
            new_card_idx = self.active_card_idx

        # Only add these once there is a seed
        if has_seed():
            import stash
            for i in range(len(accounts)):
                account = accounts[i]
                # print('account[{}]={}'.format(account, i))

                account_card = {
                    'right_icon': lv.ICON_BITCOIN,
                    'header_color': LIGHT_GREY,
                    'header_fg_color': LIGHT_TEXT,
                    'statusbar': {'title': 'ACCOUNT', 'icon': lv.ICON_FOLDER, 'fg_color': get_account_fg(account)},
                    'title': account.get('name'),
                    'page_micron': microns.PageDot,
                    'bg_color': get_account_bg(account),
                    'flow': MenuFlow,
                    'args': {'menu': account_menu, 'is_top_level': True},
                    'account': account
                }
                if len(stash.bip39_passphrase) > 0:
                    account_card['icon'] = lv.ICON_PASSPHRASE

                card_descs.append(account_card)

            # Add special accounts

            for extension in supported_extensions:
                if common.settings.get('ext.{}.enabled'.format(extension['name']), False):
                    if len(stash.bip39_passphrase) > 0:
                        extension['card']['icon'] = lv.ICON_PASSPHRASE
                    else:
                        extension['card']['icon'] = None
                    card_descs.append(extension['card'])

            # BIP 85 Page
            if common.settings.get('ext.bip85.enabled', False):
                bip85_card = {
                    'right_icon': lv.ICON_SETTINGS,
                    'header_color': LIGHT_GREY,
                    'header_fg_color': LIGHT_TEXT,
                    'statusbar': {'title': 'Extension', 'icon': lv.ICON_FOLDER, 'fg_color': WHITE},
                    'title': "BIP 85",
                    'page_micron': microns.PageDot,
                    'bg_color': BITCOIN_ORANGE,
                    'flow': MenuFlow,
                    'args': {'menu': bip85_menu, 'is_top_level': True},
                    'account': None
                }
                if len(stash.bip39_passphrase) > 0:
                    bip85_card['icon'] = lv.ICON_PASSPHRASE

                card_descs.append(bip85_card)

            more_card = {
                'statusbar': {'title': 'MORE', 'icon': lv.ICON_ADD_ACCOUNT, 'fg_color': WHITE},
                'page_micron': microns.PagePlus,
                'bg_color': DARK_GREY,
                'flow': MenuFlow,
                'args': {'menu': plus_menu, 'is_top_level': True}
            }
            card_descs.append(more_card)

        if new_card_idx is None:
            new_card_idx = 1 if len(card_descs) > 1 else 0

        # Reset the card_header to blank so nothing from the previous set carries over
        self.set_card_header(force_all=True)

        self.set_cards(card_descs, active_idx=new_card_idx)

    async def start_fcc_test(self):
        # Start the FCC Test automatically
        common.keypad.inject(lv.KEY.ENTER)

    def on_left_select(self, is_pressed):
        # Tell the micron_bar so it can update
        common.ui.set_left_pressed(is_pressed)

        # Tell the page so it can perform any action it may want
        active_page = self.get_active_page()
        if active_page is not None:
            active_page.left_action(is_pressed)

    def on_right_select(self, is_pressed):
        # Tell the micron_bar so it can update
        common.ui.set_right_pressed(is_pressed)

        # Tell the page so it can perform any action it may want
        active_page = self.get_active_page()
        if active_page is not None:
            active_page.right_action(is_pressed)

    def on_nav_left(self):
        assert(self.active_screen is not None)
        # print('on_nav_left: is_top_level={}'.format(self.is_top_level()))
        if self.is_top_level():
            self.prev_card()

    def on_nav_right(self):
        assert(self.active_screen is not None)
        # print('on_nav_right: is_top_level={}'.format(self.is_top_level()))
        if self.is_top_level():
            self.next_card()

    # Full refresh
    def full_cards_refresh(self):
        from utils import start_task

        self.update_cards()

        async def restart_main_task():
            self.start_card_task(card_idx=self.active_card_idx)

        start_task(restart_main_task())

        # self.update_screen_info(self.card_descs[self.active_card_idx])

    def start_card_task(self, new_card_desc=None, card_idx=0):
        from tasks import card_task
        from uasyncio import get_event_loop
        import gc

        if self.active_card_task is not None:
            self.active_card_task.cancel()
            # print('Old task canceled <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')

        gc.collect()
        if new_card_desc is None:
            new_card_desc = self.card_descs[card_idx]

        loop = get_event_loop()
        self.active_card_task = loop.create_task(card_task(new_card_desc))

    def update_screen_info(self, new_card_desc):
        statusbar = new_card_desc.get('statusbar')
        if statusbar is not None:
            title = statusbar.get('title')
            icon = statusbar.get('icon')
            fg_color = statusbar.get('fg_color')

            if title is not None or icon is not None:
                self.set_statusbar(title=title, icon=icon, fg_color=fg_color)

        bg_color = new_card_desc.get('bg_color')
        self.set_screen_bg_color(bg_color)

    def next_card(self):
        num_cards = len(self.card_descs)

        if num_cards == 1:
            return

        if self.active_card_idx < num_cards - 1:
            self.active_card_idx += 1
        elif self.active_card_idx == num_cards - 1:
            self.active_card_idx = 0
        new_card_desc = self.card_descs[self.active_card_idx]
        self.active_screen.card_nav.push_card(new_card_desc, self.active_card_idx)

        self.update_screen_info(new_card_desc)

        self.start_card_task(new_card_desc=new_card_desc)

    def prev_card(self):
        num_cards = len(self.card_descs)

        if num_cards == 1:
            return

        if self.active_card_idx > 0:
            self.active_card_idx -= 1
        elif self.active_card_idx == 0:
            self.active_card_idx = num_cards - 1
        new_card_desc = self.card_descs[self.active_card_idx]
        self.active_screen.card_nav.pop_card(new_card_desc, self.active_card_idx)

        self.update_screen_info(new_card_desc)

        self.start_card_task(new_card_desc=new_card_desc)

    # Mount and animate the given page so it replaces the current page with a "push" style
    def push_page(self, page):
        active_card = self.get_active_card()
        assert(active_card is not None, 'Pushing page when there is no active card!')
        active_card.set_page(page)
        # active_card.push_page(page)

    # Mount and animate the given page so it replaces the current page with a "pop" style
    def pop_page(self, page):
        active_card = self.get_active_card()
        assert(active_card is not None, 'Popping page when there is no active card!')
        active_card.set_page(page)
        # active_card.pop_page(page)

    def set_page(self, page):
        active_card = self.get_active_card()
        assert(active_card is not None, 'Setting page when there is no active card!')
        active_card.set_page(page)

    def kill_active_card_task(self):
        if self.active_card_task is not None:
            self.active_card_task.cancel()

    def set_is_top_level(self, is_top_level):
        original_value = self._is_top_level
        self._is_top_level = is_top_level
        self.active_screen.card_nav.micron_bar.show_hide_pagination()
        common.keypad.enable_global_nav_keys(self._is_top_level)
        return original_value

    def is_top_level(self):
        return self._is_top_level

    def set_battery_level(self, percent):
        self.battery_level = percent
        self.active_screen.statusbar.set_battery_level(percent)

    def set_is_charging(self, is_charging):
        self.active_screen.statusbar.set_is_charging(is_charging)

    def set_active_account(self, account):
        self.active_account = account

    def get_active_account(self):
        return self.active_account
