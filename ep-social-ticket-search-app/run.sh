#!/bin/bash
#
# Run local web app install server
#

# Settings
WWWDIR=$PWD
PORT=8000

version=`python -c 'import sys; print(sys.version_info[0])'`

if [ $version = 2 ]
then
    python -m SimpleHTTPServer $PORT
else
    python -m http.server $PORT
fi

