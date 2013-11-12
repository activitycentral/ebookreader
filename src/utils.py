import os
import platform
import md5
import sys
import shutil

ACTIVE_DESKTOP_FILE = "/home/olpc/.olpc-active-desktop"

def get_active_desktop():
    desktop = "sugar"

    if "SUGAR_BUNDLE_ID" in os.environ:
        return "Sugar"

    try:
        fd = open(ACTIVE_DESKTOP_FILE, "r")
        desktop = fd.read().strip()
        fd.close()
    except IOError, e:
        if e.errno != 2:
            desktop = "unknown"

    if "DESKTOP_SESSION" in os.environ:
        desktop = os.getenv('DESKTOP_SESSION')

    if desktop == "sugar":
        return "Sugar"
    if desktop == "sweets":
        return "Sugar"
    if desktop == "gnome":
        return "GNOME"
    if desktop == "gnome-classic":
        return "GNOME"
    if desktop == "gnome-fallback":
        return "GNOME"
    return "Unknown"

def is_machine_a_xo():
    return (os.path.exists('/boot/olpc_build') or os.path.exists('/bootpart/olpc_build'))

def is_ubuntu():
    plat, version, codename = platform.dist()
    return plat == 'Ubuntu'

def get_md5(filename):
    #FIXME: Should be moved somewhere else
    filename = filename.replace('file://', '')  # XXX: hack
    fh = open(filename)
    digest = md5.new()
    while 1:
        buf = fh.read(4096)
        if buf == "":
            break
        digest.update(buf)
    fh.close()
    return digest.hexdigest()

