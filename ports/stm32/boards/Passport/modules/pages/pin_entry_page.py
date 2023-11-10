# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# pin_entry_page.py


import lvgl as lv
from styles.colors import BLACK, TEXT_GREY, WHITE, COPPER, PIN_ENTRY_MESSAGE_COLOR
from pages import Page
from tasks import get_security_words_task
from utils import InputMode
from views import Label, View, PINInput, Icon
from constants import MENU_ITEM_CORNER_RADIUS
from styles import Stylize
from t9 import T9
import microns
import common
from common import pa

NUM_ATTEMPTS_LEFT_BRICK_WARNING = 5

NUM_DIGITS_FOR_SECURITY_WORDS = 4
MIN_PIN_LENGTH = 6
MAX_PIN_LENGTH = 12


class PINEntryPage(Page):
    def __init__(self,
                 title=None,
                 pin='',
                 security_words_message='Recognize these\nsecurity words?',
                 card_header=None,
                 statusbar=None,
                 check_pin_prefix=False,
                 left_micron=microns.Back,
                 right_micron=microns.Checkmark):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         left_micron=left_micron,
                         right_micron=right_micron)

        self.user_wants_to_see_security_words = common.settings.get('security_words', False)

        self.title = title
        self.pin = pin
        self.check_pin_prefix = check_pin_prefix
        self.security_words_message = security_words_message
        self.security_words = []

        # TODO: this should have a different name to avoid confusion with update_message(show_security_words)
        self.displaying_security_words = False
        self.security_container = None
        self.message_container = None
        self.message_icon = None
        self.message = None
        self.words_container = None
        self.brick_warning_shown = False
        if len(pin) == NUM_DIGITS_FOR_SECURITY_WORDS and self.user_wants_to_see_security_words:
            self.disable_backspace = True
        else:
            self.disable_backspace = False

        if len(pin) < NUM_DIGITS_FOR_SECURITY_WORDS and self.user_wants_to_see_security_words:
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

        if pa.attempts_left <= NUM_ATTEMPTS_LEFT_BRICK_WARNING:
            self.show_brick_warning()

        self.arrows = [lv.KEY.UP, lv.KEY.DOWN, lv.KEY.RIGHT, lv.KEY.LEFT]

    def show_brick_warning(self):
        if not self.brick_warning_shown:
            if pa.attempts_left == 1:
                message = 'This is your FINAL attempt before Passport is permanently disabled.'
            else:
                message = '{} attempts left\nuntil Passport is permanently disabled.'.format(pa.attempts_left)
            self.update_message(show_security_words=False, title='WARNING', icon='ICON_WARNING',
                                message=message, color=COPPER)
            self.brick_warning_shown = True

    def update_message(self, show_security_words=False, title=None, icon=None,
                       message=None, color=PIN_ENTRY_MESSAGE_COLOR):
        # Avoid updating if showing brick warning again
        if not show_security_words and self.brick_warning_shown:
            return

        if self.is_mounted():
            if self.message is not None:
                self.message.unmount()
                self.message = None
            if self.message_icon is not None:
                self.message_icon.unmount()
                self.message_icon = None
            if self.message_container is not None:
                self.message_container.unmount()
                self.message_container = None
            if self.words_container is not None:
                self.words_container.unmount()
                self.words_container = None
            if self.security_container is not None:
                self.security_container.unmount()
                self.security_container = None

        # Allow for a brick warning to be shown after security words were shown
        if show_security_words:
            self.brick_warning_shown = False

        # Make a fancy rounded container for the security words or a warning message
        if show_security_words or message is not None:
            self.security_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
            self.security_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.security_container) as default:
                default.radius(MENU_ITEM_CORNER_RADIUS)
                default.clip_corner(True)
                default.border_width(2)
                default.pad_row(0)
                default.border_color(color)
                default.bg_color(color)
            self.add_child(self.security_container)

            # Show the message
            self.message_container = View(flex_flow=lv.FLEX_FLOW.ROW)
            self.message_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.message_container) as default:
                default.flex_align(main=lv.FLEX_ALIGN.CENTER)
                default.bg_color(color)

            # TODO: Cleanup the alignment of the icon and message to use flex settings instead of padding
            if icon is not None:
                self.message_icon = Icon(icon, color=WHITE)
                with Stylize(self.message_icon) as default:
                    default.pad(left=8, right=0, top=8)
                self.message_container.add_child(self.message_icon)

            self.message = Label(text=title, color=WHITE, center=True)
            if icon is None:
                self.message.set_width(lv.pct(100))
            with Stylize(self.message) as default:
                default.text_align(lv.TEXT_ALIGN.CENTER)
                if show_security_words:
                    default.pad(left=8, right=8, top=4, bottom=4)
                else:
                    default.pad(left=0, right=6, top=8, bottom=8)
            self.message_container.add_child(self.message)
            self.security_container.add_child(self.message_container)

            self.words_container = View(flex_flow=lv.FLEX_FLOW.ROW)
            self.words_container.set_size(lv.pct(100), lv.SIZE.CONTENT)
            with Stylize(self.words_container) as default:
                default.radius(MENU_ITEM_CORNER_RADIUS - 2)
                default.clip_corner(True)
                if show_security_words:
                    default.pad(left=8, right=8, bottom=8, top=8)
                else:
                    default.pad(left=4, right=4, bottom=2, top=2)
                default.flex_align(main=lv.FLEX_ALIGN.SPACE_AROUND)
                default.bg_color(WHITE)

            # Show the security words or a message
            if show_security_words:
                for i in range(len(self.security_words)):
                    word_view = Label(text=self.security_words[i], color=TEXT_GREY)
                    self.words_container.add_child(word_view)
            else:
                message_view = Label(text=message, color=TEXT_GREY)
                message_view.set_width(lv.pct(100))
                with Stylize(message_view) as default:
                    default.text_align(lv.TEXT_ALIGN.CENTER)
                    default.pad(left=6, right=6, top=6, bottom=6)
                self.words_container.add_child(message_view)

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
            if self.displaying_security_words:
                self.displaying_security_words = False
                self.security_words = []
                self.update_message(show_security_words=False, title=self.security_words_message)

                if pa.attempts_left <= NUM_ATTEMPTS_LEFT_BRICK_WARNING:
                    self.show_brick_warning()

                self.t9.set_max_length(MAX_PIN_LENGTH)
                return

            pin = self.input.get_pin()
            if len(pin) >= MIN_PIN_LENGTH:
                self.set_result((pin, True))
            else:
                # TODO: Show a warning message
                # print('PIN is too short')
                pass

    def left_action(self, is_pressed):
        pin = self.input.get_pin()
        if not is_pressed:
            self.set_result((pin, False))

    def attach(self, group):
        super().attach(group)
        group.add_obj(self.lvgl_root)
        # self.lvgl_root.add_event_cb(self.on_key, lv.EVENT.KEY, None)
        common.keypad.set_intercept_key_cb(self.on_key)
        common.keypad.set_key_repeat(lv.KEY.UP, False)

    def detach(self):
        # self.lvgl_root.remove_event_cb(self.on_key)
        common.keypad.set_intercept_key_cb(None)
        common.keypad.set_key_repeat(lv.KEY.UP, True)
        lv.group_remove_obj(self.lvgl_root)
        super().detach()

    def on_key(self, key, pressed):
        # Disable backspace if viewing the security words
        if self.disable_backspace and key == lv.KEY.BACKSPACE:
            return

        if key == lv.KEY.UP:
            if pressed:
                self.input.view_pin()
            else:
                self.input.hide_pin()

        if key in self.arrows:
            return

        if pressed:
            if not self.displaying_security_words:
                self.t9.on_key(key)
                self.pin = self.t9.get_text()
                self.input.set_pin(self.pin)
                self.input.set_mode(self.t9.mode)

    async def on_security_words(self, security_words, error):
        from serializations import sha256
        # NOTE: Be aware that this is called from the context of another task
        # TODO: error not handled
        if error is None:
            self.security_words = security_words
            self.displaying_security_words = True
            new_pin_sha = sha256(self.pin)
            true_pin_sha = common.settings.get('pin_prefix_hash')
            if self.check_pin_prefix and not all(x == y for x, y in zip(new_pin_sha, true_pin_sha)):
                self.security_words_message = ("Your PIN is incorrect.\n"
                                               "Try again.")
                self.update_message(show_security_words=False, title="Warning", message=self.security_words_message)
                return

            self.update_message(show_security_words=True, title=self.security_words_message)

        if not self.displaying_security_words and pa.attempts_left <= NUM_ATTEMPTS_LEFT_BRICK_WARNING:
            self.show_brick_warning()

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
                # Prevent user from backspacing to index all security words
                self.disable_backspace = True
            else:
                self.disable_backspace = False
                self.update_message(show_security_words=False, title=self.security_words_message)

            # If user goes back below the minimum, then we need to show security words again
            if len(prefix) < NUM_DIGITS_FOR_SECURITY_WORDS:
                self.t9.set_max_length(NUM_DIGITS_FOR_SECURITY_WORDS)

        if pa.attempts_left <= NUM_ATTEMPTS_LEFT_BRICK_WARNING:
            self.show_brick_warning()
