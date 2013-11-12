from gi.repository import Gtk

import constants

class AlignedWidgetsCombo(Gtk.HBox):
    def __init__(self, icon, label, alignment):
        Gtk.HBox.__init__(self)
        self.set_homogeneous(True)

        spacing = 5

        if (alignment == constants.TEXT_ORIENTATION_RIGHT) or \
           (alignment == constants.TEXT_ORIENTATION_TOP):
            first_widget = label
            second_widget = icon
        else:
            first_widget = icon
            second_widget = label

        if alignment == constants.TEXT_ORIENTATION_LEFT:
            left_container = Gtk.HBox()
            left_container.pack_start(Gtk.Label('    '), False, False, 0)
            middle_container = None
            right_container = Gtk.HBox()
            container = left_container
        elif alignment == constants.TEXT_ORIENTATION_MIDDLE:
            left_container = Gtk.HBox()
            middle_container = Gtk.HBox()
            right_container = Gtk.HBox()
            container = middle_container
        elif alignment == constants.TEXT_ORIENTATION_RIGHT:
            left_container = Gtk.HBox()
            middle_container = None
            right_container = Gtk.HBox()
            container = right_container
        elif alignment == constants.TEXT_ORIENTATION_TOP:
            left_container = Gtk.HBox()
            middle_container = Gtk.VBox()
            right_container = Gtk.HBox()
            container = middle_container
        elif alignment == constants.TEXT_ORIENTATION_BOTTOM:
            left_container = Gtk.HBox()
            middle_container = Gtk.VBox()
            right_container = Gtk.HBox()
            container = middle_container

        self.pack_start(left_container, True, True, 0)
        if middle_container is not None:
            self.pack_start(middle_container, True, True, 0)
        self.pack_start(right_container, True, True, 0)

        if alignment == constants.TEXT_ORIENTATION_RIGHT:
            container.pack_end(Gtk.Label('    '), False, False, 0)
            container.pack_end(second_widget, False, False, 0)
            container.set_spacing(spacing)
            container.pack_end(first_widget, False, False, 0)
        else:
            container.pack_start(first_widget, False, False, 0)
            container.set_spacing(spacing)
            container.pack_start(second_widget, False, False, 0)

        self.show_all()
