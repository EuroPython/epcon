#!/bin/sh
#
# Run local web app install server
#

# Settings
WWWDIR=$PWD
PORT=8000

# Start web server
python -m SimpleHTTPServer $PORT
