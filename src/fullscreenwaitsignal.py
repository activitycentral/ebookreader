from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from overlaywidget import OverlayWidget

class FullScreenWaitSignal(OverlayWidget):

    def __init__(self):
        self._icon = Icon(icon_name='bookreader-wait-1',
                          icon_size=Gtk.IconSize.LARGE_TOOLBAR)
        OverlayWidget.__init__(self, self._icon)

        self.set_size_request(Gdk.Screen.get_default().get_width(),
                              Gdk.Screen.get_default().get_height())

        self._hidden = True
        self._func_id = GObject.timeout_add(500, self.__update_icon)

    def _reposition(self):
        x_position = 0
        y_position = 0
        self.move(x_position, y_position)

    def show_overlay_widget(self):
        self._counter = 1
        self._reposition()
        self.show()

        self._hidden = False

    def __update_icon(self):
        if self._hidden is True:
            return True

        if self._counter == 5:
            self._counter = 0

        self._counter = self._counter + 1
        self._icon.props.icon_name = 'bookreader-wait-' + str(self._counter)

        return True

    def hide_overlay_widget(self):
        self._hidden = True
        self.hide()
