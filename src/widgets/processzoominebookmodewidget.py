from gi.repository import Gtk
from gi.repository import Gdk

from gettext import gettext as _
from sugar3.graphics.icon import Icon

from mode import Mode
from widgets import constants
from widgets.iconandlabelscombo import IconAndLabelsCombo
from widgets.modescomboheader import ModesComboHeader

from overlaywidget import OverlayWidget

class ProcessZoomInEBookModeWidget(OverlayWidget, Mode, ModesComboHeader):

    def __init__(self, app):
        Mode.__init__(self, app)
	self._app = app
        self.box = Gtk.VBox()
        self._keys = ['dummy_key', 'KP_Up', 'KP_Down']


        OverlayWidget.__init__(self, self.box)
        ModesComboHeader.__init__(self, constants.MODE_ZOOM, self,
                                  'bookreader-dummy-zoom', app, False)

        self._screen = Gdk.Screen.get_default()

        self.set_size_request(self._width, self._height)

    def init_key_handler_map_if_not_already(self):
        if self._key_handler_map is not None:
            return

        view = self._app.get_reader_tab()

        self._key_handler_map = {
                'KP_Home' : [self.switch_to_normal_mode],
                'KP_End'  : [self.switch_to_normal_mode],
                'KP_Left' : [self.handle_left_navigation_key],
                'KP_Right': [self.handle_right_navigation_key],
                'KP_Up'   : [self.show_icon_and_execute_function, (view.secondary_toolbar.dummy_view_toolbar._zoom_in_cb, 'KP_Up',)],
                'KP_Down' : [self.show_icon_and_execute_function, (view.secondary_toolbar.dummy_view_toolbar._zoom_out_cb, 'KP_Down',)],
                'a'       : [self.switch_to_normal_mode],
                'd'       : [self.switch_to_normal_mode],
                                }

    def show_icon_and_execute_function(self, callback, keyname):
        self.__show_appropriate_icon(keyname)
        callback(None)
        self.show_idle_state()

    def __show_appropriate_icon(self, key_pressed):
        for child in self.box.get_children():
            self.box.remove(child)

        self.__add_all()
        self.box.pack_start(self._icons[key_pressed], True, True, 0)
        self.box.show_all()
        self.show_overlay_widget()
        self._app.window.force_ui_updates()

    def show_idle_state(self):
        self.__show_appropriate_icon(self._keys[0])

    def __add_all(self):
        view = self._app.get_reader_tab()._view

        if isinstance(view, Gtk.Label):
            return

        self._icons = {}

        self.__add_icon_rows([(self._keys[0], 'bookreader-wheel-vert'),])
        self.__add_icon_rows([(self._keys[1], 'bookreader-wheel-vert-up'),])
        self.__add_icon_rows([(self._keys[2], 'bookreader-wheel-vert-down'),])

    def __add_icon_rows(self, icon_names):
        zoom_icons = self._app.get_reader_tab()._view.get_zoom_icons()
        zoom_text = self.ebooreader.get_reader_tab()._view.get_zoom_text()

        left_dummy_text = self.__get_dummy_text_of_size_n(14)
        right_dummy_text = self.__get_dummy_text_of_size_n(len(zoom_text))

        for item in icon_names:
            (key, centre_icon_name) = item
            self._icons[key] = IconAndLabelsCombo(centre_icon_name,
                    [(zoom_text, constants.WIDGET_TYPE_LABEL, constants.TEXT_ORIENTATION_LEFT),
                     (left_dummy_text, constants.WIDGET_TYPE_LABEL, constants.TEXT_ORIENTATION_LEFT),
                     (right_dummy_text, constants.WIDGET_TYPE_LABEL, constants.TEXT_ORIENTATION_RIGHT),
                     (zoom_icons[0], constants.WIDGET_TYPE_ICON,  constants.TEXT_ORIENTATION_TOP),
                     (zoom_icons[1], constants.WIDGET_TYPE_ICON,  constants.TEXT_ORIENTATION_BOTTOM),])

    def __get_dummy_text_of_size_n(self, n):
        text = ''
        for i in range(0, n):
            text = text + ' '
        return text

    def show_overlay_widget(self):
        if len(self.box.get_children()) == 0:
            return

        self._navigator.update_zoom_icons()
        self._reposition()
        self.show()
