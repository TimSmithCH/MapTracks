#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

ls -lR tracks/
git status
git add tracks/geojson
git commit

rm -r test
rm -r node_modules
