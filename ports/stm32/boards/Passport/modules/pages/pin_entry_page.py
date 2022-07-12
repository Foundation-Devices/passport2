# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# pin_entry_page.py


import lvgl as lv
from styles.colors import BLACK, FD_BLUE, TEXT_GREY, WHITE
from pages import Page
from tasks import get_security_words_task
from utils import InputMode
from views import Label, View, PINInput
from constants import MENU_ITEM_CORNER_RADIUS
from styles import Stylize
from t9 import T9
import microns
import common

NUM_DIGITS_FOR_SECURITY_WORDS = 4
MIN_PIN_LENGTH = 6
MAX_PIN_LENGTH = 12


class PINEntryPage(Page):
    def __init__(self,
                 title=None,
                 pin='',
                 confirm_security_words=True,
                 security_words_message='Recognize these security words?',
                 card_header=None,
                 statusbar=None,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)

        self.user_wants_to_see_security_words = common.settings.get('security_words', False)

        self.title = title
        self.pin = pin
        self.confirm_security_words = confirm_security_words
        self.security_words_message = security_words_message
        self.security_words = []

        self.show_security_words = False
        self.security_container = None
        self.message_container = None
        self.words_container = None

        if self.user_wants_to_see_security_words:
            initial_max_length = NUM_DIGITS_FOR_SECURITY_WORDS
        else:
            initial_max_length = MAX_PIN_LENGTH

        self.t9 = T9(text=self.pin,
                     cursor_pos=len(self.pin),
                     mode=InputMode.NUMERIC,
                     max_length=initial_max_length,
                     on_ready=self.on_ready,
                     allow_cursor_keys=False)

        with Stylize(self) as default:
            default.pad_row(4)

        if self.title is not None:
            self.title_view = Label(text=self.title, color=BLACK)
            self.title_view.set_width(lv.pct(100))
            with Stylize(self.title_view) as default:
                default.text_color(TEXT_GREY)
                default.text_align(lv.TEXT_ALIGN.CENTER)
            self.add_child(self.title_view)

        self.input = PINInput(pin=self.pin, input_mode=InputMode.NUMERIC)
        self.input.set_width(lv.pct(100))
        self.add_child(self.input)

        self.update_security_words()

    def update_security_words(self):
        if self.is_mounted():
            if self.message_container is not None:
                self.message_container.unmount()
                self.message_container = None
            if self.words_container is not None:
                self.words_container.unmount()
                self.words_container = None
            if self.security_container is not None:
                self.security_container.unmount()
                self.security_container = None

        if self.show_security_words and self.user_wants_to_see_security_words:
            # Make a fancy rounded container for the security words
            self.security_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
            self.security_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.security_container) as default:
                default.radius(MENU_ITEM_CORNER_RADIUS)
                default.clip_corner(True)
                default.border_width(2)
                default.pad_row(0)
                default.border_color(FD_BLUE)
                default.bg_color(FD_BLUE)
            self.add_child(self.security_container)

            # Show the message
            self.message_container = View()
            self.message_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.message_container) as default:
                default.bg_color(FD_BLUE)

            self.message = Label(text=self.security_words_message, color=WHITE)
            self.message.set_width(lv.pct(100))
            with Stylize(self.message) as default:
                default.text_align(lv.TEXT_ALIGN.CENTER)
                default.pad(left=6, right=6, top=8, bottom=8)
            self.message_container.add_child(self.message)
            self.security_container.add_child(self.message_container)

            # Show the words
            self.words_container = View(flex_flow=lv.FLEX_FLOW.ROW)
            self.words_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.words_container) as default:
                default.radius(MENU_ITEM_CORNER_RADIUS - 2)
                default.clip_corner(True)
                default.pad(left=16, right=16, bottom=10, top=10)
                default.flex_align(main=lv.FLEX_ALIGN.SPACE_BETWEEN)
                default.bg_color(WHITE)

            for i in range(len(self.security_words)):
                word_view = Label(text=self.security_words[i], color=TEXT_GREY)
                self.words_container.add_child(word_view)

            self.security_container.add_child(self.words_container)

        if self.is_mounted():
            if self.security_container is not None:
                self.security_container.mount(self.lvgl_root)
            if self.message_container is not None:
                self.message_container.mount(self.security_container.lvgl_root)
            if self.words_container is not None:
                self.words_container.mount(self.security_container.lvgl_root)

    def right_action(self, is_pressed):
        if not is_pressed:
            if self.show_security_words and self.user_wants_to_see_security_words:
                self.show_security_words = False
                self.security_words = []
                self.update_security_words()
                self.t9.set_max_length(MAX_PIN_LENGTH)
                return

            pin = self.input.get_pin()
            if len(pin) >= MIN_PIN_LENGTH:
                self.set_result(pin)
            else:
                # TODO: Show a warning message
                # print('PIN is too short')
                pass

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)
        self.lvgl_root.add_event_cb(self.on_key, lv.EVENT.KEY, None)

    def detach(self):
        self.lvgl_root.remove_event_cb(self.on_key)
        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def on_key(self, event):
        key = event.get_key()

        if not self.show_security_words:
            self.t9.on_key(key)
            self.pin = self.t9.get_text()
            self.input.set_pin(self.pin)
            self.input.set_mode(self.t9.mode)

        if self.user_wants_to_see_security_words:
            self.update_security_words()

    async def on_security_words(self, security_words, error):
        # NOTE: Be aware that this is called from the context of another task
        if error is None:
            self.security_words = security_words
            self.show_security_words = True
            self.update_security_words()

    def on_ready(self, prefix):
        from utils import start_task

        if self.user_wants_to_see_security_words:
            # Only perform security words check here when input is ready, otherwise user might enter
            # the first press of a multi-key input on the fourth character and it's the wrong one.
            # print('on_ready("{}")'.format(prefix))
            if len(prefix) == NUM_DIGITS_FOR_SECURITY_WORDS:
                # TODO: Lookup security words in a task (have to do this way as we are not being called
                #       in an async context).
                start_task(get_security_words_task(self.on_security_words, prefix))
            else:
                self.show_security_words = False
            self.update_security_words()

            # If user goes back below the minimum, then we need to show security words again
            if len(prefix) < NUM_DIGITS_FOR_SECURITY_WORDS:
                self.t9.set_max_length(NUM_DIGITS_FOR_SECURITY_WORDS)
