#!/bin/sh
set -e
 
WD=$PWD

COMMIT=$(git log|head -n 1 | cut -d" " -f2 |cut -c-8)
DATE=$(date +%Y%m%d)
ACTVERSION=$(grep activity_version ../sugar/activity/activity.info |cut -d" " -f3)
APP=EBookReader
DATADIR=${APP}_$ACTVERSION
TMP=$(mktemp -d)

mkdir $TMP/$DATADIR

# Building GNOME installer
cp -a ../src $TMP/$DATADIR/GNOME
cp -a ../gnome/* $TMP/$DATADIR/GNOME
cp -a ../lib/* $TMP/$DATADIR/GNOME
cp -a ../icons $TMP/$DATADIR/GNOME
find $TMP/$DATADIR -type f | egrep pyc$ | xargs -r rm
sh makeself/makeself.sh $TMP/$DATADIR/GNOME $DATADIR.run "$APP" ./install.sh
chmod 755 $DATADIR.run


# Building SUGAR installer
cp -a ../src $TMP/$DATADIR/SUGAR
cp -a ../sugar/* $TMP/$DATADIR/SUGAR
cp -a ../lib/* $TMP/$DATADIR/SUGAR
cp -a ../icons $TMP/$DATADIR/SUGAR
find $TMP/$DATADIR -type f | egrep pyc$ | xargs -r rm
cd $TMP
mv $DATADIR/SUGAR $APP.activity
zip -r $WD/$DATADIR.xo $APP.activity

cd $WD
if [ -d "../installers" ]
then
	echo ../installers folder already exist
else
	echo creating ../installers folder
	mkdir ../installers
fi

mv $DATADIR.run ../installers/
mv $DATADIR.xo  ../installers

rm -rf $TMP
echo $DATADIR "(Gnome/Sugar)" were created
