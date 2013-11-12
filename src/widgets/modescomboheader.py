from gi.repository import Gtk
from gi.repository import Gdk

import constants

from gettext import gettext as _

from sugar3.graphics.icon import Icon
from ReadTab import evinceadapter, epubadapter

class _ModesComboHeaderNavigator:
    def __init__(self, app):
       	self._app = app
	self._modes = {}
        self._icon_size = Gtk.IconSize.LARGE_TOOLBAR
	
    def get_new_header(self, icon_header):
        event_box = Gtk.EventBox()
        event_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))

        container = Gtk.HBox()
        event_box.add(container)

        self._highest_mode = -1
        self._current_mode = constants.MODE_ZOOM

        container.pack_start(Gtk.VBox(), True, True, 0)

        self._middle_container = Gtk.HBox()
        self._middle_container.pack_start(Gtk.VBox(), True, True, 0)
        icons_container = Gtk.HBox()
        self._middle_container.pack_start(icons_container, True, True, 0)
        self._middle_container.pack_start(Gtk.VBox(), True, True, 0)
        container.pack_start(self._middle_container, True, True, 0)

        container.pack_start(Gtk.VBox(), True, True, 0)


        # Add the "left arrow" icon, irrespective.
        icons_container.pack_start(Icon(icon_name='bookreader-left',
                                        icon_size=self._icon_size),
                                        True, True, 0)

        for icon_name in ['bookreader-dummy-zoom', 'bookreader-libraries']:
            if icon_name.startswith(icon_header):
                icon_name = icon_name + '-click'
            else:
                icon_name = icon_name + '-select'

            icon = Icon(icon_name=icon_name, icon_size=self._icon_size)
            icons_container.pack_start(icon, True, True, 0)

            if icon_name.startswith('bookreader-dummy-zoom'):
                self._zoom_icon = icon

        # Add the "right arrow" icon, irrespective.
        icons_container.pack_start(Icon(icon_name='bookreader-right',
                                        icon_size=self._icon_size),
                                        True, True, 0)


        event_box.show_all()
        return event_box

    def get_new_footer(self, show_select_option):
        bottom_note = Gtk.HBox()
        bottom_note.set_spacing(10)

        right_container = \
                self.__get_right_aligned_note_and_label_icon('bookreader-gamekeys-menu',
                                                             _('Exit'), bottom_note)
        if show_select_option:
            bottom_note.pack_end(Icon(icon_name='bookreader-divider',
                                      icon_size=Gtk.IconSize.LARGE_TOOLBAR),
                                 False, False, 0)
            self.__get_right_aligned_note_and_label_icon('bookreader-gamekeys-enter',
                                                          _('Select'), bottom_note)

        event_box = Gtk.EventBox()
        event_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))
        event_box.add(bottom_note)

        event_box.show_all()

        return event_box

    def __get_right_aligned_note_and_label_icon(self, icon_name, text,
                                                container):
        label = Gtk.Label()
        label.set_markup('<span color="white">' + text +'</span>');
        container.pack_end(Icon(icon_name=icon_name,
                                icon_size=Gtk.IconSize.LARGE_TOOLBAR),
                                False, False, 0)
        container.pack_end(label, False, False, 0)

    def add_mode(self, mode, mode_widget, icon_header, app,
                 show_select_option):
        self._app = app

        if mode in self._modes.keys():
            return

        self._modes[mode] = mode_widget
        self._modes.keys().sort()

        mode_widget._header = self.get_new_header(icon_header)
        mode_widget.get_overlaid_widget().pack_start(mode_widget._header, False, False, 0)
        mode_widget.get_overlaid_widget().reorder_child(mode_widget._header, 0)

        mode_widget._footer = self.get_new_footer(show_select_option)
        mode_widget.get_overlaid_widget().pack_start(mode_widget._footer, False, False, 0)

        if mode > self._highest_mode:
            self._highest_mode = mode

    def switch_mode(self, mode):
        self._current_mode = mode

        if len(self._modes.keys()) > 1:
            self._app.set_mode(self._app._modes[mode])

        mode_widget = self._modes[mode]
        mode_widget.show_overlay_widget()

    def go_to_previous_mode(self):
        index = None
        for key in range(1, len(self._modes.keys())):
            if self._current_mode == self._modes.keys()[key]:
                index = key
                break

        if index is not None:
            self.switch_mode(self._modes.keys()[index - 1])

    def is_previous_mode_possible(self):
        return self._current_mode != self._modes.keys()[0]

    def go_to_next_mode(self):
        index = None
        for key in range(0, len(self._modes.keys())):
            if self._current_mode == self._modes.keys()[key]:
                index = key
                break

        if index is not None:
            self.switch_mode(self._modes.keys()[index + 1])

    def is_next_mode_possible(self):
        return (self._current_mode != self._modes.keys()[-1]) and \
               (len(self._modes.keys()) != 1)

    def update_zoom_icons(self):
        for key in self._modes.keys():
            self.__update_icons_for_mode_widget(self._modes[key])

    def __update_icons_for_mode_widget(self, mode_widget):
        view = self._app.get_reader_tab()._view

        if isinstance(view, Gtk.Label):
            return

        zoom_icon = mode_widget._header.get_children()[0].get_children()[1].get_children()[1].get_children()[1]

        if isinstance(view, evinceadapter.EvinceViewer):
            if self._current_mode == constants.MODE_ZOOM:
                zoom_icon.props.icon_name = 'bookreader-popup-zoom-click'
            else:
                zoom_icon.props.icon_name = 'bookreader-popup-zoom-select'
        elif isinstance(view, epubadapter.EpubViewer):
            if self._current_mode == constants.MODE_ZOOM:
                zoom_icon.props.icon_name = 'bookreader-popup-textsize-click'
            else:
                zoom_icon.props.icon_name = 'bookreader-popup-textsize-select'


_navigator = None

def get_modes_navigator(app):
    global _navigator
    if _navigator is None:
        _navigator = _ModesComboHeaderNavigator(app)
    return _navigator


class ModesComboHeader:
    def __init__(self, mode, mode_widget, icon_header, app,
                 show_select_option):
        self._navigator = get_modes_navigator(app)
        self._mode_widget = mode_widget
        self._app = app

        self._navigator.add_mode(mode, mode_widget, icon_header, app,
                                 show_select_option)

    def handle_left_navigation_key(self):
        if self._navigator.is_previous_mode_possible():
            self._mode_widget.hide()
            self._navigator.go_to_previous_mode()
            self._navigator.update_zoom_icons()

    def handle_right_navigation_key(self):
        if self._navigator.is_next_mode_possible():
            self._mode_widget.hide()
            self._navigator.go_to_next_mode()
            self._navigator.update_zoom_icons()

    def switch_to_normal_mode(self):
        self._navigator._current_mode = constants.MODE_ZOOM
        self._app.set_mode(self._app._modes[constants.MODE_NORMAL])
        self.hide()
