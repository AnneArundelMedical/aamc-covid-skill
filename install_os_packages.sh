#!/bin/sh

PKGS_FILE=os_packages.txt

if [ ! -e "$PKGS_FILE" ] ; then
  echo "Packages file '$PKGS_FILE' not found." >/dev/stderr
  exit 1
fi

for pkg in $(cat "$PKGS_FILE") ; do
  apt install "$pkg"
done

