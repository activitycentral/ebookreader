from gi.repository import Gtk

import constants
from sugar3.graphics.icon import Icon

class IconAndLabelsCombo(Gtk.VBox):
    def __init__(self, centre_icon_name, widgets_info_list):
        Gtk.VBox.__init__(self)

        self._top_box = Gtk.VBox()
        self._middle__box = Gtk.VBox()
        self._bottom_box = Gtk.VBox()

        self.pack_start(self._top_box, True, True, 0)
        self.pack_start(self._middle__box, True, True, 0)
        self.pack_start(self._bottom_box, True, True, 0)


        self._icon = Icon(icon_name=centre_icon_name,
                          icon_size=Gtk.IconSize.LARGE_TOOLBAR)

        self._icon_container = Gtk.HBox()
        self._icon_container.pack_start(self._icon, False, False, 0)
        self._icon_container.set_spacing(16)

        self._another_level = Gtk.HBox()
        self._middle__box.pack_start(self._another_level, True, True, 0)

        for widget_info in widgets_info_list:
            (info, widget_type, orientation) = widget_info

            if widget_type == constants.WIDGET_TYPE_LABEL:
                widget = Gtk.Label(info)
            elif widget_type == constants.WIDGET_TYPE_ICON:
                widget = Icon(icon_name=info,
                              icon_size=Gtk.IconSize.LARGE_TOOLBAR)

            self.add_widget(widget, orientation)

        self._another_level.pack_start(Gtk.HBox(), True, True, 0)
        self._another_level.pack_start(self._icon_container, True, True, 0)
        self._another_level.pack_start(Gtk.HBox(), True, True, 0)

    def add_widget(self, widget, orientation):
        if orientation == constants.TEXT_ORIENTATION_TOP:
            self._top_box.pack_end(widget, False, False, 0)
        elif orientation == constants.TEXT_ORIENTATION_LEFT:
            self._icon_container.pack_start(widget, False, False, 0)
            self._icon_container.reorder_child(widget, 0)
        elif orientation == constants.TEXT_ORIENTATION_RIGHT:
            self._icon_container.pack_start(widget, False, False, 0)
        elif orientation == constants.TEXT_ORIENTATION_BOTTOM:
            self._bottom_box.pack_start(widget, False, False, 0)

        self.show_all()
