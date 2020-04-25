#!/bin/bash
set -e   # Exit with nonzero exit code if anything fails
set -x   # Debug mode to echo commands

TOKEN=$(<tileset_api)

tilesets list-sources --token $TOKEN timsmithch
tilesets update-recipe --token $TOKEN timsmithch.all_tracks ./all_tracks_recipe.json
tilesets publish --token $TOKEN timsmithch.all_tracks

rm tileset_ap*
