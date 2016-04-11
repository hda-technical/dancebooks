#!/bin/sh

cd /home/georg/repo/dancebooks.testing

PDF=test.pdf

GIT_SSH="scripts/ssh-wrapper.sh" \
git pull

make clean
rm -f "$PDF"

PATH="/home/georg/texmf/bin/x86_64-linux:$PATH" \
make "$PDF"

make clean
mv "$PDF" "www/static/files/$PDF"

