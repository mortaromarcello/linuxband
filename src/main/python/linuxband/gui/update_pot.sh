#!/bin/bash
if [ -z ${1} ]; then
  echo -e "${0} <progname>"
fi
prog=${1}
xgettext -k_ -kN_ -o ${prog}.pot *.py
