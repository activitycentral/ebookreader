from gi.repository import Gtk
from gi.repository import Gdk

from overlaywidget import OverlayWidget
from sugar3.graphics.icon import Icon

class BookmarkOverlayWidget(Icon):
    def __init__(self):
        Icon.__init__(self, icon_name='bookreader-mark',
                            icon_size=Gtk.IconSize.LARGE_TOOLBAR)

        self.props.halign = Gtk.Align.END
        self.props.valign = Gtk.Align.START

    def show_overlay_widget(self):
        self.show()
