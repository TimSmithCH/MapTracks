#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

pwd
env
ls -l
which node
npm config list
npm config ls -l
ls -lR tracks/

rm -r test
rm -r node_modules
