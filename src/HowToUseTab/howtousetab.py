from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import WebKit

import os
import env_settings as env
from gettext import gettext as _

from ebookreadertab import EBookReaderTab


class SecondaryToolBar(Gtk.HBox):
    def __init__(self):
        Gtk.HBox.__init__(self)

        self._event_box = Gtk.EventBox()
        self._event_box.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse('#000000'))
        self._event_box.add(self)

        version_text = _('About BookReader: Version') + ' 1.1'
        label = Gtk.Label()
        label.set_markup('<span color="white">' + version_text +'</span>')
        self.pack_start(label, True, True, 0)
        self.show_all()


class HowToUseTab(EBookReaderTab):
    def __init__(self, app):
        EBookReaderTab.__init__(self, app)
        self.secondary_toolbar = SecondaryToolBar()

        sw = Gtk.ScrolledWindow()
        view = WebKit.WebView()

        self.add(sw)
        sw.add(view)
        view.open(os.path.join(env.SUGAR_ACTIVITY_ROOT,
                               'HowToUseTab',
                               'Guia Lector Ceibal.html'))

        self.show_all()

    def get_tab_label(self):
        return _('How To Use')

    def get_tab_toolbar(self):
        return self.secondary_toolbar._event_box

    def get_tab_toolbar_icon_name(self):
        return 'bookreader-guide'
