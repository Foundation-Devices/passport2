# SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundation.xyz>
# SPDX-License-Identifier: GPL-3.0-or-later
#
# view.py - Base class for all Views


class View():
    '''Base class for all composable View objects.'''

    def __init__(self, flex_flow=None, children=None):
        self.flex_flow = flex_flow
        self.lvgl_root = None
        self.group = None
        self.children = children
        self.styles = []
        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.scroll_dir = None
        self.set_flags = 0
        self.clear_flags = 0
        self.set_state_flags = 0
        self.clear_state_flags = 0

    def set_children(self, children):
        '''Set the entire list of children all at once.'''
        self.children = children
        if self.is_mounted():
            self.mount_children()

    def add_child(self, child):
        '''Append a child to the list of children.'''
        if self.children is None:
            self.children = []
        self.children.append(child)

    def remove_child(self, child):
        if child in self.children:
            self.children.remove(child)

    def insert_child(self, index, child):
        '''Append a child to the list of children.'''
        if self.children is None:
            self.children = []
        self.children.insert(index, child)

    def add_style(self, style):
        '''Append a style to the list of styles for this View.'''
        self.styles.append(style)

    def reset_styles(self):
        '''Remove all styles from the View.'''
        self.styles = []

    def is_mounted(self):
        '''True if the View has been mounted, False if not.'''
        return self.lvgl_root is not None

    def is_attached(self):
        '''True if the View has been mounted, False if not.'''
        return self.group is not None

    def set_size(self, width, height):
        '''Set the width and height of the View.'''
        self.width = width
        self.height = height
        if self.is_mounted():
            self.lvgl_root.set_size(self.width, self.height)

    def set_width(self, width):
        '''Set the width of the View, updating it immediately if mounted.'''
        self.width = width
        if self.is_mounted() and self.width is not None:
            self.lvgl_root.set_width(self.width)

    def set_height(self, height):
        '''Set the height of the View, updating it immediately if mounted.'''
        self.height = height
        if self.is_mounted() and self.height is not None:
            self.lvgl_root.set_height(self.height)

    def set_pos(self, x, y):
        '''Set the x and y position of the View, updating it immediately if mounted.'''
        self.set_x(x)
        self.set_y(y)

    def set_x(self, x):
        '''Set the x position of the View, updating it immediately if mounted.'''
        self.x = x
        if self.is_mounted() and self.x is not None:
            self.lvgl_root.set_x(self.x)

    def set_y(self, y):
        '''Set the y position of the View, updating it immediately if mounted.'''
        self.y = y
        if self.is_mounted() and self.y is not None:
            self.lvgl_root.set_y(self.y)

    def set_no_scroll(self):
        import lvgl as lv
        '''Set the View to not scroll, updating the setting immediately if mounted.'''
        self.set_scroll_dir(lv.DIR.NONE)

    def set_scroll_dir(self, dir):
        '''Set the View's scroll direction (lv.DIR.NONE, lv.DIR.HOR, lv.DIR.VER), updating the setting immediately
        if mounted.'''
        self.scroll_dir = dir
        if self.is_mounted():
            self.lvgl_root.set_scroll_dir(self.scroll_dir)

    def add_flag(self, flag):
        self.set_flags |= flag
        self.clear_flags &= ~flag  # Keep the flags consistent
        if self.is_mounted():
            self.lvgl_root.add_flag(flag)

    def clear_flag(self, flag):
        self.clear_flags |= flag
        self.set_flags &= ~flag  # Keep the flags consistent
        if self.is_mounted():
            self.lvgl_root.clear_flag(flag)

    def add_state(self, state):
        self.set_state_flags |= state
        self.clear_state_flags &= ~state  # Keep the style consistent
        if self.is_mounted():
            self.lvgl_root.add_state(state)

    def clear_state(self, state):
        self.clear_state_flags |= state
        self.set_state_flags &= ~state  # Keep the style consistent
        if self.is_mounted():
            self.lvgl_root.clear_state(state)

    def create_lvgl_root(self, lvgl_parent):
        from views import Container
        '''Hook to allow subclasses to specify a different base lvgl widget, while still getting all the benefits
        of mount().'''
        return Container(lvgl_parent, flex_flow=self.flex_flow)

    def get_lvgl_root(self):
        '''Get the root lvgl object for this View.'''
        return self.lvgl_root

    def mount(self, lvgl_parent):
        '''Create the underlying lvgl widget(s) that render this view.  The widgets are
           persistent as long as the View is shown, and can be updated by calling the
           standard lvgl functions on the widgets.

           Subclasses MUST call this method as super().mount(lvgl_parent).
        '''

        # Cleanup in case we force a re-render() without a push or pop
        self.unmount()

        # Setup the root container
        self.lvgl_root = self.create_lvgl_root(lvgl_parent)

        if self.width is not None:
            self.lvgl_root.set_width(self.width)
        if self.height is not None:
            self.lvgl_root.set_height(self.height)
        if self.x is not None:
            self.lvgl_root.set_x(self.x)
        if self.y is not None:
            self.lvgl_root.set_y(self.y)
        if self.scroll_dir is not None:
            self.lvgl_root.set_scroll_dir(self.scroll_dir)
        if self.set_flags is not 0:
            # NOTE: add_flag() can set multiple flags at once OR'd together
            self.lvgl_root.add_flag(self.set_flags)
        if self.clear_flags is not 0:
            # NOTE: clear_flag() can clear multiple flags at once OR'd together
            self.lvgl_root.clear_flag(self.clear_flags)
        if self.set_state_flags is not 0:
            # NOTE: add_state() can set multiple flags at once OR'd together
            self.lvgl_root.add_state(self.set_state_flags)
        if self.clear_state_flags is not 0:
            # NOTE: clear_State() can clear multiple flags at once OR'd together
            self.lvgl_root.clear_state(self.clear_state_flags)

        # Apply the styles
        for style in self.styles:
            style.apply(self.lvgl_root)

        self.mount_children()

        return self.lvgl_root

    def mount_children(self):
        # Mount children
        if self.children is not None:
            # print('self.children: {}'.format(self.children))
            for child in self.children:
                # print('child: {}'.format(child))
                child.mount(self.lvgl_root)

    def unmount(self):
        '''Release all lvgl resources associated with this View.

        Subclasses MUST call this method as super().unmount().
        '''
        # import gc
        # gc.collect()
        if self.is_mounted():
            self.unmount_children()

            self.lvgl_root.delete()
            self.lvgl_root = None

    def unmount_children(self):
        # Unmount children
        if self.children is not None:
            for child in self.children:
                child.unmount()

    def attach(self, group):
        '''Attach any objects to the lvgl indev group necessary for user interaction.

           Views are attach()ed after any animation is complete.'''
        self.group = group

    def detach(self):
        '''Detach any objects from groups, and remove any event callbacks that were
        configured in attach()'''
        self.group = None
