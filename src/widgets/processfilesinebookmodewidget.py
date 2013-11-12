from gi.repository import Gtk
from gi.repository import Gdk
import os

from mode import Mode
from widgets import constants
from widgets.modescomboheader import ModesComboHeader

from MyLibraryTab.mylibrarytab import TreeView

from sugar3.graphics.icon import Icon

from overlaywidget import OverlayWidget
from GetBooksTab import readerUtilities as RU

class ProcessFilesInEBookModeWidget(OverlayWidget, Mode, ModesComboHeader):

    def __init__(self, app):
        Mode.__init__(self, app)
	self._app = app
        self.box = Gtk.VBox()

        OverlayWidget.__init__(self, self.box)
        ModesComboHeader.__init__(self, constants.MODE_SELECT_FILE, self,
                                  'bookreader-libraries', app, True)

        self._screen = Gdk.Screen.get_default()

        self.set_size_request(self._width, self._height)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.box.pack_start(sw, True, True, 0)

        self._treeview = TreeView()
        sw.add(self._treeview)

        self._my_library_tab = self._app.get_my_library_tab()

    def setup(self):
        self._treeview.get_model().clear()
        self._my_library_tab.load_ebooks(self._treeview)

        self.box.show_all()


    def init_key_handler_map_if_not_already(self):
        if self._key_handler_map is not None:
            return

        self._key_handler_map = {
                'KP_Home' : [self.switch_to_normal_mode],
                'KP_Left' : [self.handle_left_navigation_key],
                'KP_Right': [self.handle_right_navigation_key],
                'KP_Up'   : [self._my_library_tab.select_previous_entry, (self._treeview,)],
                'Up'   : [self._my_library_tab.select_previous_entry, (self._treeview,)],
                'KP_Down' : [self._my_library_tab.select_next_entry, (self._treeview,)],
                'Down' : [self._my_library_tab.select_next_entry, (self._treeview,)],
                'KP_End'  : [self._my_library_tab.load_selected_entry, (None, self._treeview,)],
                'a'       : [self.switch_to_normal_mode],
                'd'       : [self._my_library_tab.load_selected_entry, (None, self._treeview,)],
                                }
