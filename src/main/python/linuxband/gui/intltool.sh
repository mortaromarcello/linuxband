#!/bin/bash
if [ -z $1 ]; then
  echo -e "${0} <language> <program>"
fi
lang=${1}
prog=${2}
#intltool-extract --type=gettext/glade test2.glade
xgettext -k_ -kN_ -o ${prog}.pot *.py
msginit -l ${lang}
msgmerge -U ${lang}.po ${prog}.pot
if [ ! -d "locale/${lang}/LC_MESSAGES/" ]; then
  mkdir -p locale/${lang}/LC_MESSAGES/
fi
msgfmt ${lang}.po -o locale/${lang}/LC_MESSAGES/${prog}.mo
