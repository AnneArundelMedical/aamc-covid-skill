#!/bin/sh

PKGS_FILE=os_packages.txt

if [ ! -e "$PKGS_FILE" ] ; then
  echo "Packages file '$PKGS_FILE' not found." >/dev/stderr
  exit 1
fi

while read pkg ; do
  FIRST_LETTER=$(echo "$pkg" | head -c 1)
  if [ "$FIRST_LETTER" != "#" ] ; then
    echo "INSTALLING PACKAGE: $pkg" >/dev/stderr
    apt install "$pkg" || {
      echo "INSTALL FAILED, ABORTING." >/dev/stderr
      exit 1
    }
  fi
done < "$PKGS_FILE"

