#!/bin/sh

set -x
aclocal 
libtoolize --force --copy
autoheader
automake --foreign --add-missing --copy
autoconf

