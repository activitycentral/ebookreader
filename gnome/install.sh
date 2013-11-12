#!/bin/sh

echo "Clean previous installation"
rm -rf $HOME/E$APP $HOME/.local/share/applications/EBookReader.desktop $HOME/.local/share/applications/gnome-ebookreader.desktop $HOME/.local/share/mime/packages/org.ac.EBookReader.xml
rm -f $HOME/.local/share/applications/userapp-abrir-libro.py-P14OVW.desktop
APP=EBookReader
TARGET=$HOME/$APP


rm -rf $TARGET

echo "Copyng files to $TARGET"
cp . -a $TARGET

echo "Installing icon on GNOME menu"
sed "s:REPLACE:$TARGET:" $TARGET/$APP.desktop -i
cp $TARGET/$APP.desktop $HOME/.local/share/applications/
update-desktop-database $HOME/.local/share/applications/

echo "Setting $APP as default view for pdf, epub, pdfceibal y epubceibal"
xdg-mime default $APP.desktop application/pdf
xdg-mime default $APP.desktop application/epub+zip
xdg-mime default $APP.desktop application/x-ceibal


echo "Deleting temporary files"
cd /
rm $OLDPWD -rf

# --------------

COMPLETED="$APP Installation finished successfully"

if [ 1$DISPLAY != 1 ] ; then
  if which zenity >/dev/null ; then
      zenity --info --text "$COMPLETED" --title="Installation finished successfully"
  fi
fi


echo $COMPLETED
