# SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# backup_code_page.py


import lvgl as lv
from styles import Stylize
from styles.colors import TEXT_GREY
from pages import Page
from views import BackupCodeSection, Label
from keys import KEY_0, KEY_9
from utils import flatten_list, split_backup_code
from constants import (NUM_BACKUP_CODE_SECTIONS, NUM_DIGITS_PER_BACKUP_CODE_SECTION, TOTAL_BACKUP_CODE_DIGITS)
import microns
import common


class BackupCodePage(Page):

    def __init__(self, digits=[None] * TOTAL_BACKUP_CODE_DIGITS, editable=True,
                 card_header=None, statusbar=None,
                 left_micron=microns.Back, right_micron=microns.Checkmark):
        super().__init__(
            flex_flow=lv.FLEX_FLOW.COLUMN,
            card_header=card_header,
            statusbar=statusbar,
            right_micron=right_micron,
            left_micron=left_micron)

        # Check length of digits
        assert(len(digits) == TOTAL_BACKUP_CODE_DIGITS)

        # Split up the digits
        self.digits = digits
        self.digits_by_row = split_backup_code(self.digits)

        self.editable = editable
        self.prev_top_level = None

        self.curr_row = 0
        self.curr_col = 0
        self.sections = []

        # self.set_size(lv.pct(100), lv.pct(100))
        with Stylize(self) as default:
            # default.radius(4)
            default.pad(left=4, right=4, bottom=1, top=4)
            default.pad_row(5)

        # Add the sections
        for row in range(NUM_BACKUP_CODE_SECTIONS):
            section = BackupCodeSection(
                self.digits_by_row[row],
                editable=self.editable,
                focused_idx=self.curr_col if row == self.curr_row else None)
            section.set_size(lv.pct(100), lv.SIZE.CONTENT)
            self.add_child(section)
            self.sections.append(section)

    def right_action(self, is_pressed):
        if not is_pressed:
            backup_code = flatten_list(self.digits_by_row)
            self.set_result(backup_code)

    def left_action(self, is_pressed):
        if not is_pressed:
            self.set_result(None)

    def attach(self, group):
        super().attach(group)

        if self.editable:
            group.add_obj(self.lvgl_root)
            self.lvgl_root.add_event_cb(self.on_key, lv.EVENT.KEY, None)
            self.curr_section().focus(self.curr_col)

            self.prev_top_level = common.ui.set_is_top_level(False)

    def detach(self):
        if self.editable:
            common.ui.set_is_top_level(self.prev_top_level)
            self.lvgl_root.remove_event_cb(self.on_key)
            lv.group_remove_obj(self.lvgl_root)

        super().detach()

    def on_key(self, event):
        if not self.editable:
            return

        key = event.get_key()
        if key == lv.KEY.RIGHT:
            self.next_col()
        elif key == lv.KEY.LEFT:
            self.prev_col()
        elif key == lv.KEY.UP:
            self.prev_row()
        elif key == lv.KEY.DOWN:
            self.next_row()
        elif key == lv.KEY.BACKSPACE:
            self.delete_digit()
        elif key >= KEY_0 and key <= KEY_9:
            self.set_digit(key - KEY_0)

    def curr_section(self):
        return self.sections[self.curr_row]

    def set_digit(self, digit, goto_next=True):
        self.digits_by_row[self.curr_row][self.curr_col] = digit
        self.curr_section().set_digits(self.digits_by_row[self.curr_row])
        if goto_next:
            self.next_digit()

    def delete_digit(self):
        self.set_digit(None, goto_next=False)
        self.prev_digit()

    def prev_digit(self):
        if not self.prev_col():
            if self.prev_row():
                # Only update if we changed rows upward
                self.curr_col = NUM_DIGITS_PER_BACKUP_CODE_SECTION - 1
                self.curr_section().set_focused_idx(self.curr_col)

    def next_digit(self):
        if not self.next_col():
            if self.next_row():
                # Only update if we changed rows downward
                self.curr_col = 0
                self.curr_section().set_focused_idx(self.curr_col)

    def prev_col(self):
        if self.curr_col > 0:
            self.curr_col -= 1
            self.curr_section().set_focused_idx(self.curr_col)
            return True
        elif self.curr_row > 0:
            # Wrap around to previous row and last col
            self.curr_section().defocus()
            self.curr_row -= 1
            self.curr_col = NUM_DIGITS_PER_BACKUP_CODE_SECTION - 1
            self.curr_section().focus(self.curr_col)
            return True
        else:
            return False

    def next_col(self):
        if self.curr_col < NUM_DIGITS_PER_BACKUP_CODE_SECTION - 1:
            self.curr_col += 1
            self.curr_section().set_focused_idx(self.curr_col)
            return True
        elif self.curr_row < NUM_BACKUP_CODE_SECTIONS - 1:
            self.curr_section().defocus()
            self.curr_row += 1
            self.curr_col = 0
            self.curr_section().focus(self.curr_col)
            return True
        else:
            return False

    def prev_row(self):
        if self.curr_row > 0:
            self.curr_section().defocus()
            self.curr_row -= 1
            self.curr_section().focus(self.curr_col)
            return True
        else:
            return False

    def next_row(self):
        if self.curr_row < NUM_BACKUP_CODE_SECTIONS - 1:
            self.curr_section().defocus()
            self.curr_row += 1
            self.curr_section().focus(self.curr_col)
            return True
        else:
            return False
