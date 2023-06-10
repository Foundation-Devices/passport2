# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# table.py - An LVGL table component wrapper

import lvgl as lv
from views import View
from styles.colors import WHITE, TEXT_GREY
from styles import Stylize

class Table(View):
    def __init__(self,
                 items=[],
                 col_width=212,
                 default_icon=lv.ICON_FILE,
                 alt_icon=lv.ICON_FOLDER,
                 get_cell_info=None):
        super().__init__()
        self.items = items
        self.col_width = col_width
        self.default_icon = default_icon
        self.alt_icon = alt_icon
        self.get_cell_info = get_cell_info

        with Stylize(self, lv.PART.ITEMS) as default:
            default.pad(bottom=11, top=12)

    def set_src(self, src):
        self.src = src
        self.update()

    def draw_part_begin_event_cb(self, e):
        dsc = lv.obj_draw_part_dsc_t.__cast__(e.get_param())

        # If the cells are drawn...
        if dsc.part == lv.PART.ITEMS:
            label_dsc = lv.draw_label_dsc_t.__cast__(dsc.label_dsc)
            label_dsc.ofs_x += 28

    def draw_part_end_event_cb(self, e):
        dsc = lv.obj_draw_part_dsc_t.__cast__(e.get_param())

        # If the cells are being drawn...
        if dsc.part == lv.PART.ITEMS:

            # Draw the icon
            obj = e.get_target()
            is_alt_icon = obj.has_cell_ctrl(dsc.id, 0, lv.table.CELL_CTRL.CUSTOM_1)

            icon_area = lv.area_t()
            icon = None
            if is_alt_icon:
                icon = self.alt_icon
            else:
                icon = self.default_icon

            selected_row = self.get_selected_row()
            col_count = self.lvgl_root.get_row_cnt()
            draw_row = dsc.id % col_count

            selected = draw_row == selected_row
            if selected:
                icon_color = WHITE
            else:
                icon_color = TEXT_GREY

            icon_img_dsc = lv.draw_img_dsc_t()
            icon_img_dsc.init()
            icon_img_dsc.recolor = icon_color
            icon_img_dsc.recolor_opa = 255

            # Setup the draw area
            icon_area.x1 = 10 + dsc.draw_area.x1
            icon_area.y1 = dsc.draw_area.y1 + ((dsc.draw_area.y2 - dsc.draw_area.y1) - icon.header.h) // 2
            icon_area.x2 = icon_area.x1 + icon.header.w - 1
            icon_area.y2 = icon_area.y1 + icon.header.h - 1

            lv.draw_img(icon_area, dsc.clip_area, icon, icon_img_dsc)

    def create_lvgl_root(self, lvgl_parent):
        table = lv.table(lvgl_parent)

        for i, item in enumerate(self.items):
            if self.get_cell_info is not None:
                (label, is_alt_icon) = self.get_cell_info(item)
            else:
                label = item
                is_alt_icon = False

            table.set_cell_value(i, 0, label)
            if is_alt_icon:
                table.add_cell_ctrl(i, 0, lv.table.CELL_CTRL.CUSTOM_1)
            else:
                table.clear_cell_ctrl(i, 0, lv.table.CELL_CTRL.CUSTOM_1)

        table.set_col_width(0, self.col_width)

        # Add an event callback to apply some custom drawing
        table.add_event_cb(self.draw_part_begin_event_cb, lv.EVENT.DRAW_PART_BEGIN, None)
        table.add_event_cb(self.draw_part_end_event_cb, lv.EVENT.DRAW_PART_END, None)
        # table.add_event_cb(self.change_event_cb, lv.EVENT.VALUE_CHANGED, None)
        return table

    def get_selected_row(self):
        row = lv.C_Pointer()
        _col = lv.C_Pointer()
        self.lvgl_root.get_selected_cell(row, _col)
        return row.uint_val

