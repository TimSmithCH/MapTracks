#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

tilesets list-sources --token `cat tileset_api` timsmithch
rm tileset_ap*
