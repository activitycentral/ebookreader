#!/bin/sh
APP=EBookReader
echo "Removing files"
rm -rf $HOME/$APP $HOME/.local/share/applications/EBookReader.desktop $HOME/.local/share/applications/gnome-ebookreader.desktop
rm -f $HOME/.local/share/applications/userapp-abrir-libro.py-P14OVW.desktop

rm -rf $HOME/$APP
rm -f $HOME/.local/share/mime/packages/org.ac.EBookReader.xml
rm -f $HOME/.local/share/applications/EBookReader.desktop

echo "Updating databases"
update-mime-database $HOME/.local/share/mime/
update-desktop-database $HOME/.local/share/applications/

echo "Done"
