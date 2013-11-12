from gi.repository import Gtk

from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton

class SecondaryToolbarButton(ToolButton):
    """
    By definition, since this is a button, there will ALWAYS be a
    callback function associated.
    """
    def __init__(self, icon_name, tooltip_label=None, callback=None,
                       icon_size=Gtk.IconSize.LARGE_TOOLBAR,accelerator=None, **kwargs):
        icon = Icon(icon_name=icon_name, icon_size=icon_size)

        ToolButton.__init__(self, icon_widget=icon)

        if tooltip_label is not None:
            self.set_tooltip(tooltip_label)

        if callback is not None:
            self.connect('clicked', callback)
