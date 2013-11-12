from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import Icon

class OverlayWidget(Gtk.Window):

    def __init__(self, widget_to_overlay):
        Gtk.Window.__init__(self)
        self._box = Gtk.VBox()
        self._widget_to_overlay = widget_to_overlay

        self.set_decorated(False)
        self.set_resizable(False)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        self.set_border_width(0)

        self.props.accept_focus = False

        self._box.add(widget_to_overlay)
        self._box.show_all()

        self.add(self._box)

        self._width = 1000
        self._height = 400

    def _reposition(self):
        x_position = (self._screen.get_width())/2 - (self._width / 2)
        y_position = (self._screen.get_height())/2 -  (self._height / 2)

        self.move(x_position, y_position)

    def show_overlay_widget(self):
        self.setup()
        self._reposition()
        self.show()

    def get_overlaid_widget(self):
        return self._box

    def setup(self):
        pass
