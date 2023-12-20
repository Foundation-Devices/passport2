# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# predictive_text_input_page.py


import lvgl as lv
from styles.colors import BLACK, SCROLLBAR_BG_COLOR
from pages import Page
from utils import InputMode, set_list
from views import TextInput, Label, View, ListItem, TextInput
from styles import Stylize
from keys import KEY_0, KEY_9
import microns
from predictive_utils import get_words_matching_prefix, word_to_keypad_numbers, get_last_word
import passport


class PredictiveTextInputPage(Page):
    '''
    Handle the entry of 1 or more words using predictive input from a list of words.
    '''

    def __init__(self,
                 title='Enter word {word_idx} of {total_words}',
                 word_list='bip39',
                 total_words=24,
                 card_header=None,
                 statusbar=None,
                 initial_words=[],
                 initial_prefixes=[],
                 left_micron=microns.Back,
                 right_micron=microns.Forward):
        super().__init__(card_header=card_header,
                         statusbar=statusbar,
                         right_micron=right_micron,
                         left_micron=left_micron,
                         flex_flow=lv.FLEX_FLOW.COLUMN)

        self.title = title
        self.word_list = word_list
        self.total_words = total_words
        self.word_idx = 0
        self.prediction_idx = 0
        self.selected_words = initial_words
        self.prefixes = initial_prefixes
        self.predictions = []

        with Stylize(self) as default:
            default.pad(top=6)

        if self.title is not None:
            self.title_view = Label(text=self.get_title(), color=BLACK)
            self.title_view.set_width(lv.pct(100))
            with Stylize(self.title_view) as default:
                default.text_align(lv.TEXT_ALIGN.CENTER)
            self.add_child(self.title_view)

        self.initial_prefix = self.prefixes[self.word_idx] if len(self.prefixes) > 0 else ''

        self.input = TextInput(text=self.initial_prefix, input_mode=InputMode.NUMERIC)
        self.input.set_width(lv.pct(100))
        with Stylize(self.input) as default:
            default.flex_align(main=lv.FLEX_ALIGN.CENTER, cross=lv.FLEX_ALIGN.CENTER, track=lv.FLEX_ALIGN.CENTER)
        self.add_child(self.input)

        self.predictions_container = View(flex_flow=lv.FLEX_FLOW.COLUMN)
        self.predictions_container.set_width(lv.pct(100))

        with Stylize(self.predictions_container) as default:
            default.flex_fill()
            default.pad_row(0)

        # Adjust scrollbar position
        with Stylize(self.predictions_container, selector=lv.PART.SCROLLBAR) as scrollbar:
            scrollbar.pad(right=0)
            if not passport.IS_COLOR:
                scrollbar.bg_color(SCROLLBAR_BG_COLOR)

        self.add_child(self.predictions_container)

        self.update_predictions()

    def update_title(self):
        self.title_view.set_text(self.get_title())

    def update_predictions(self):
        if self.is_mounted():
            prefix = self.input.get_text()
        else:
            prefix = self.initial_prefix

        if len(prefix) > 0:
            # print('Lookup words for {}'.format(prefix))
            set_list(self.prefixes, self.word_idx, prefix)
            self.predictions = get_words_matching_prefix(prefix, max=5, word_list=self.word_list)
        elif self.word_idx == self.total_words - 1:
            self.predictions = [get_last_word(self.selected_words)]
        else:
            self.predictions = []

        # Ensure we restrict the prediction_idx in case the number of entries got smaller than
        # the current index
        num_predictions = len(self.predictions)
        # print('>>> num_predictions={} prefix="{}"'.format(num_predictions, prefix))
        # print('>>> predictions="{}"'.format(self.predictions))

        if self.prediction_idx > num_predictions - 1:
            self.prediction_idx = max(num_predictions - 1, 0)

        if self.is_mounted():
            self.predictions_container.unmount_children()
            self.predictions_container.set_children([])

        # print('predictions={}'.format(self.predictions))
        # print('selected_words={}'.format(self.selected_words))

        # Create the new children
        if num_predictions > 0:
            # Use the predictions
            items = self.predictions
        else:
            # Show a placeholder
            items = ['No Matches']

        for i in range(len(items)):
            item = ListItem(label=items[i], center=True, icon=None)
            if i == self.prediction_idx:
                # print('Add focus for index {}'.format(self.prediction_idx))
                item.add_state(lv.STATE.FOCUS_KEY)
            self.predictions_container.add_child(item)

        if self.is_mounted():
            self.predictions_container.mount_children()
            if num_predictions > 0:
                self.predictions_container.children[self.prediction_idx].lvgl_root.scroll_to_view(lv.ANIM.ON)

    def update_highlighted(self):
        # Create the new children
        for i in range(len(self.predictions)):
            item = self.predictions_container.children[i]
            if i == self.prediction_idx:
                item.add_state(lv.STATE.FOCUS_KEY)
            else:
                item.clear_state(lv.STATE.FOCUS_KEY)

        self.predictions_container.children[self.prediction_idx].lvgl_root.scroll_to_view(lv.ANIM.ON)

    def get_title(self):
        return self.title.format(word_idx=self.word_idx + 1, total_words=self.total_words)

    def right_action(self, is_pressed):
        if not is_pressed:
            # TODO: Get the index of the selected word (see how menu_page does it)
            #       Then add to the list of words
            if len(self.predictions) > 0:
                set_list(self.selected_words, self.word_idx, self.predictions[self.prediction_idx])

                # Fill out the prefix to the full length of the selected word so the prediction
                # list has a single item in it.
                set_list(self.prefixes, self.word_idx, str(
                    word_to_keypad_numbers(self.predictions[self.prediction_idx])))
                # print('selected_words={}'.format(self.selected_words))
                if len(self.selected_words) == self.total_words and self.word_idx == self.total_words - 1:
                    # print('Returning selected_words and prefixes!')
                    self.set_result((self.selected_words, self.prefixes))
                    return
                else:
                    # Reset (or lookup the prediction prefix and go to the next word index
                    self.word_idx += 1
                    prefix_text = ''
                    if self.word_idx < len(self.prefixes):
                        prefix_text = self.prefixes[self.word_idx]
                    self.input.set_text(prefix_text)

                    self.update_title()
                    self.update_predictions()

    def left_action(self, is_pressed):
        if not is_pressed:
            if self.word_idx > 0:
                self.word_idx -= 1
                prefix_text = ''
                if len(self.prefixes) >= self.word_idx:
                    prefix_text = self.prefixes[self.word_idx]
                self.input.set_text(prefix_text)

                self.update_title()
                self.update_predictions()
            else:
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
        # print('KEY!')
        key = event.get_key()
        if key == lv.KEY.RIGHT:
            self.input.cursor_right()
        elif key == lv.KEY.LEFT:
            self.input.cursor_left()
        elif key == lv.KEY.UP:
            if self.prediction_idx > 0:
                self.prediction_idx -= 1
                self.update_highlighted()
        elif key == lv.KEY.DOWN:
            if self.prediction_idx < len(self.predictions) - 1:
                self.prediction_idx += 1
                self.update_highlighted()
        elif key == lv.KEY.BACKSPACE:
            self.input.del_char()
            self.update_predictions()
        elif key >= KEY_0 and key <= KEY_9:
            self.input.add_char(chr(key))
            self.update_predictions()
