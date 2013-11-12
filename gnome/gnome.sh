#!/bin/bash

cd $(dirname $0)

if [ -d /opt/sweets ]; then
# On classmate
export GTK_PATH=/opt/sweets/sugar-artwork/lib/gtk-2.0
export GTK_DATA_PREFIX=/opt/sweets/sugar-artwork/
export SUGAR_TOOLKIT_PREFIX=/opt/sweets/sugar-toolkit/
export SUGAR_PREFIX=/opt/sweets/sugar-base/
export XCURSOR_PATH=/opt/sweets/sugar-artwork/share/icons
export SUGAR_SHELL_PREFIX=/opt/sweets/sugar/
export LIBXUL_DIR=/usr/lib/xulrunner-1.9.2.18
export PYTHONPATH=/opt/sweets/sugar/src:/opt/sweets/python-xklavier/python:/opt/sweets/sugar-toolkit/src:/opt/sweets/sugar-base/:/opt/sweets/sugar-presence-service/src:/opt/sweets/sugar-toolkit/src:/opt/sweets/sugar-base/:/opt/sweets/sugar-datastore/src:/opt/sweets/sugar-toolkit/src:/opt/sweets/sugar-base/
export XDG_DATA_DIRS=/opt/sweets/sugar/share:/opt/sweets/telepathy-salut/share:/opt/sweets/telepathy-mission-control/share:/opt/sweets/telepathy-gabble/share:/opt/sweets/sugar-presence-service/share:/opt/sweets/telepathy-salut/share:/opt/sweets/telepathy-gabble/share:/opt/sweets/sugar-datastore/share:/opt/sweets/sugar-artwork/share:/usr/local/share/:/usr/share/
export PKG_CONFIG_PATH=/opt/sweets/telepathy-glib/lib/pkgconfig:/opt/sweets/telepathy-mission-control/lib/pkgconfig:/opt/sweets/telepathy-glib/lib/pkgconfig:/opt/sweets/telepathy-glib/lib/pkgconfig:/opt/sweets/libnice/lib/pkgconfig:/opt/sweets/telepathy-glib/lib/pkgconfig:/opt/sweets/telepathy-glib/lib/pkgconfig:/opt/sweets/libnice/lib/pkgconfig
else
# On XO
export GTK_PATH=/usr/lib/gtk-2.0
export GTK_DATA_PREFIX=""
fi

python launch.py "$1"
