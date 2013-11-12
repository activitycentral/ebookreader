#!/bin/sh

if [ -n "$1" ]; then
    FILES_TO_CONVERT="$@"
else
    FILES_TO_CONVERT="$(find . -name '*.py')"
fi

for f in $FILES_TO_CONVERT; do
    perl -i -0 \
    -pe "s/import sugar/import sugar3/g;" \
    -pe "s/from sugar /from sugar3 /g;" \
    -pe "s/from sugar\./from sugar3\./g;" \
    -pe "s/sugar\./sugar3\./g;" \
    $f
done
