import os
from gi.repository import Gtk
from gi.repository import Gdk
import subprocess

from gettext import gettext as _

from utils import get_active_desktop, is_machine_a_xo
from sugar3.graphics.window import Window
from sugar3.graphics.icon import Icon

class EBookReaderWindow(Window):
    def __init__(self, main_instance):
        Window.__init__(self)

        self.set_title(_('Lector Ceibal'))
        self.set_icon_from_file('./icons/bookreader-activ.svg')

        self._main_instance = main_instance
        self._ebookreader_fullscreen_in_normal_mode = False
        self._enable_fullscreen_mode = True

        if get_active_desktop() != "Sugar":
            self.set_type_hint(Gdk.WindowTypeHint.NORMAL)

        os.environ['GTK_DATA_PREFIX'] = os.getcwd() + "/"
        if is_machine_a_xo():
            rc = '100'
        else:
            rc = '72'
        Gtk.Settings.get_default().set_property('gtk-theme-name', rc)
        Gtk.Settings.get_default().set_property('gtk-icon-theme-name', 'sugar')


    def fullscreen(self, normal_mode=True):
        if normal_mode:
            self._ebookreader_fullscreen_in_normal_mode = True

        if self._is_fullscreen is True:
            return

        for toolbar in self._main_instance._tab_toolbars_list:
            toolbar.hide()
        super(EBookReaderWindow, self).fullscreen()
        Gtk.Window.fullscreen(self)

    def unfullscreen(self, normal_mode=True):
        if normal_mode:
            self._ebookreader_fullscreen_in_normal_mode = False

        for toolbar in self._main_instance._tab_toolbars_list:
            toolbar.show()
        super(EBookReaderWindow, self).unfullscreen()
        Gtk.Window.unfullscreen(self)

    def force_ui_updates(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
