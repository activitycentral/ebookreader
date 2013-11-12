from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from gettext import gettext as _

from overlaywidget import OverlayWidget

from widgets import constants
from widgets.alignedwidgetscombo import AlignedWidgetsCombo

from sugar3.graphics.icon import Icon

class ProcessBookmarksInEBookModeWidget(OverlayWidget):

    def __init__(self, app):
        self._app = app
        self._key_handler_map = None

        self.box = Gtk.VBox()
        self._keys = ['KP_Page_Up', 'dummy_key', 'KP_End', 'KP_Page_Down']
        self._icons = {}

        OverlayWidget.__init__(self, self.box)
        self._screen = Gdk.Screen.get_default()
        self._height = 240

        self.set_size_request(self._width, self._height)

    def init_key_handler_map_if_not_already(self):
        if self._key_handler_map is not None:
            return

        view = self._app.get_reader_tab()

        self._key_handler_map = {
                'KP_Page_Up'  : view._prev_bookmark_activate_cb,
                'KP_End'      : view._toggle_bookmark_activate_cb,
                'KP_Page_Down': view._next_bookmark_activate_cb,
                                }

    def do_operation(self, keyname):
        self.init_key_handler_map_if_not_already()

        self.add_all(keyname)

        from utils import is_machine_a_xo
        if is_machine_a_xo() is True:
            self.show_overlay_widget()
            self._app.window.force_ui_updates()

            GObject.timeout_add(1000,
                                self.__call_right_game_key_method_after_wait, keyname)
        else:
            self.__call_right_game_key_method_after_wait(keyname)

    def __call_right_game_key_method_after_wait(self, keyname):
        self.hide()
        self._app.window.force_ui_updates()

        self._key_handler_map[keyname](None)

        # Finally, revert to "normal" mode.
        self._app.set_mode(self._app._modes[constants.MODE_NORMAL])

    def add_all(self, key_pressed):
        for child in self.box.get_children():
            self.box.remove(child)

        self.__add_icon_rows([
            (self._keys[0], 'bookreader-gamekeys-0', _('Previous Bookmark'), constants.TEXT_ORIENTATION_TOP),
                             ])

        self.__add_icon_rows([
            (self._keys[1], 'bookreader-gamekeys-menu', _('Options'), constants.TEXT_ORIENTATION_RIGHT),
            (self._keys[2], 'bookreader-gamekeys-enter', _('Toggle Bookmark'), constants.TEXT_ORIENTATION_LEFT),
                             ])

        self.__add_icon_rows([
            (self._keys[3], 'bookreader-gamekeys-x', _('Next Bookmark'), constants.TEXT_ORIENTATION_BOTTOM),
                             ])


        # Change the icon-corresponding-to-key-pressed to "clicked" (if
        # at all).
        if key_pressed in self._keys:
            icon, event_box = self._icons[key_pressed]

            icon.props.icon_name = icon.props.icon_name + '-click'
            event_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#b3b310'))

    def __add_icon_rows(self, icon_names):
        box = Gtk.HBox(homogeneous=True)
        for item in icon_names:
            (key, centre_icon_name, text, text_orientation) = item

            icon = Icon(icon_name=centre_icon_name, icon_size=Gtk.IconSize.LARGE_TOOLBAR)

            event_box = Gtk.EventBox()
            label = Gtk.Label(text)
            event_box.add(label)

            widget = AlignedWidgetsCombo(icon, event_box, text_orientation)
            self._icons[key] = (icon, event_box)

            box.pack_start(widget, True, True, 0)

        self.box.pack_start(box, False, False, 0)
        box.show_all()
