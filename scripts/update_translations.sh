cd ../src

mkdir -p locale/es/LC_MESSAGES

xgettext -f po/POTFILES.in  --output=po/EBookReader.pot

msgmerge -o es_update.po po/es.po po/EBookReader.pot 
mv es_update.po po/es.po 

msgfmt -o locale/es/LC_MESSAGES/org.ac.EBookReader.mo po/es.po
cp locale/es/LC_MESSAGES/org.ac.EBookReader.mo locale/es_UY/LC_MESSAGES/org.ac.EBookReader.mo

cd -
