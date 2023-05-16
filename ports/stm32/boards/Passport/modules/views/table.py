# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# table.py - An LVGL table component wrapper

import lvgl as lv
# from styles import Stylize, LocalStyle
from views import View
from styles.colors import WHITE, TEXT_GREY

class Table(View):
    def __init__(self, items=[], col_widths=[212]):
        super().__init__()
        self.items = items
        self.col_widths = col_widths

    def set_src(self, src):
        self.src = src
        self.update()

    def change_event_cb(self, e):
        print('change event!')
        # obj = e.get_target()
        row = lv.C_Pointer()
        col = lv.C_Pointer()
        self.lvgl_root.get_selected_cell(row, col)
        print("row: ",row.uint_val)

        # chk = table.has_cell_ctrl(row.uint_val, 0, lv.table.CELL_CTRL.CUSTOM_1)
        # if chk:
        #     table.clear_cell_ctrl(row.uint_val, 0, lv.table.CELL_CTRL.CUSTOM_1)
        # else:
        #     table.add_cell_ctrl(row.uint_val, 0, lv.table.CELL_CTRL.CUSTOM

    def draw_part_begin_event_cb(self, e):
        dsc = lv.obj_draw_part_dsc_t.__cast__(e.get_param())

        # If the cells are drawn...
        if dsc.part == lv.PART.ITEMS:
            label_dsc = lv.draw_label_dsc_t.__cast__(dsc.label_dsc)
            # print("draw 3: dir rect_dsc={}".format(dir(label_dsc)))
            label_dsc.ofs_x += 28
                                
    def draw_part_end_event_cb(self, e):
        print("Draw part end 1")
        dsc = lv.obj_draw_part_dsc_t.__cast__(e.get_param())

        # If the cells are drawn...
        if dsc.part == lv.PART.ITEMS:

            #     # If the cells are drawn...
            #     print("Draw part end 3")
            #     if dsc.part == lv.PART.ITEMS:
            # Draw the icon
            obj = e.get_target()
            is_folder = obj.has_cell_ctrl(dsc.id, 0, lv.table.CELL_CTRL.CUSTOM_1)

            icon_area = lv.area_t()
            icon = None
            if is_folder:
                print("FOLDER-----------------------------------------")
                icon = lv.ICON_FOLDER
            else:
                print("FILE-------------------------------------------")
                icon= lv.ICON_FILE

            # print("dir(dsc)={}".format(dir(dsc)))
            print("p1={} p2={}".format(dsc.p1, dsc.p2))

            selected_row  = self.get_selected_row()
            col_count = self.lvgl_root.get_row_cnt()
            print("--> id={}".format(dsc.id))
            draw_row = dsc.id % col_count
            draw_col = dsc.id // col_count

            print("--> selected_row={}".format(selected_row))
            print("--> draw_row={}".format(draw_row))
            print("--> draw_col={}".format(draw_col))
            selected = draw_row == selected_row
            if selected:
                print("Draw WHITE icon")
                icon_color = WHITE
            else:
                print("Draw grey icon")
                icon_color = TEXT_GREY


            icon_img_dsc = lv.draw_img_dsc_t()
            icon_img_dsc.init()
            icon_img_dsc.recolor = icon_color
            icon_img_dsc.recolor_opa=255

            print("draw_area: x1={} x2={} y1={} y2={}".format(
                dsc.draw_area.x1,
                dsc.draw_area.x2,
                dsc.draw_area.y1,
                dsc.draw_area.y2
            ))

            # Setup the draw area
            icon_area.x1 = 10 + dsc.draw_area.x1
            icon_area.y1 = dsc.draw_area.y1 + ((dsc.draw_area.y2 - dsc.draw_area.y1) - icon.header.h) // 2
            icon_area.x2 = icon_area.x1 + icon.header.w - 1
            icon_area.y2 = icon_area.y1 + icon.header.h - 1
            print("icon_area: x1={} x2={} y1={} y2={}".format(
                icon_area.x1,
                icon_area.x2,
                icon_area.y1,
                icon_area.y2
            ))

            print("clip_area: x1={} x2={} y1={} y2={}".format(
                dsc.clip_area.x1,
                dsc.clip_area.x2,
                dsc.clip_area.y1,
                dsc.clip_area.y2
            ))
            # lv.draw_rect(icon_area, dsc.clip_area, rect_dsc)
            lv.draw_img(icon_area, dsc.clip_area, icon, icon_img_dsc)
            print("===============================================")


    def create_lvgl_root(self, lvgl_parent):
        table = lv.table(lvgl_parent)

        # root.set_row_cnt(len(self.items))
        # root.set_col_cnt(len(self.col_widths))

        # Don't make the cell pressed, we will draw something different in the event
        # table.remove_style(None, lv.PART.ITEMS | lv.STATE.PRESSED)

        for i, item in enumerate(self.items):
            # print("data: {}: {}".format(i, item))
            (filename, _full_path, is_folder) = item
            # root.set_cell_value(i, 0, ">" if is_folder else "F")
            table.set_cell_value(i,0, filename)
            if is_folder:
                table.add_cell_ctrl(i, 0, lv.table.CELL_CTRL.CUSTOM_1)
            else:
                table.clear_cell_ctrl(i, 0, lv.table.CELL_CTRL.CUSTOM_1)

        for i, width in enumerate(self.col_widths):
            # print("width: {}: {}".format(i, width))
            table.set_col_width(i, width)

        # Add an event callback to apply some custom drawing
        table.add_event_cb(self.draw_part_begin_event_cb, lv.EVENT.DRAW_PART_BEGIN, None)
        table.add_event_cb(self.draw_part_end_event_cb, lv.EVENT.DRAW_PART_END, None)
        table.add_event_cb(self.change_event_cb, lv.EVENT.VALUE_CHANGED, None)
        return table

    def get_selected_row(self):
        row = lv.C_Pointer()
        _col = lv.C_Pointer()
        self.lvgl_root.get_selected_cell(row, _col)
        print("row: {}".format(row.uint_val))
        return row.uint_val