# MapTracks
![MapTracks Build](https://github.com/TimSmithCH/MapTracks/workflows/MapTracks%20Build/badge.svg)

Layout tracks of outings on a map

- Download fit+gpx files from Strava to tracks/4_logged
  - By running [TimSmithCH/Strava_Pull](https://github.com/TimSmithCH/Strava_Pull)

- Remove chaff, trim and drop unnecessary fields, then upload to tracks/3_gpx
  - Interactive track-point editing [TimSmithCH/MapTracks/clipper.html](https://github.com/TimSmithCH/MapTracks/tree/master/clipper.html)
  - Batch trimming resolution and dropping blanks etc gpx_name_set.py
  - Push to GitHub repository to trigger _GitHub Actions_

- Transform and simplify gpx to GeoJson files and upload to tracks/2_geojson
  - _GitHub Actions_ runs upon MapTracks push
  - Run ogr2ogr within [TimSmithCH/MapTracks/scripts/generate_geojson.sh](https://github.com/TimSmithCH/MapTracks/tree/master/scripts/generate_geojson.sh)
    - Drops the timing info on tracks for privacy/efficieny 
    - Applies [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm) to simplify the tracks for overviewing 
- Aggregate GeoJson files and upload to tracks/1_display
  - Run geojson_merge within [TimSmithCH/MapTracks/scripts/generate_geojson.sh](https://github.com/TimSmithCH/MapTracks/tree/master/scripts/generate_geojson.sh)
- Deploy result to GitHub Pages

- Generate MapBox tileset from tracks/1_display files
  - Using MapBox Studio tileset commands in [TimSmithCH/MapTracks/scripts/deploy_tileset.sh](https://github.com/TimSmithCH/MapTracks/tree/master/scripts/deploy_tileset.sh)


View resultant [map](https://timsmithch.github.io/MapTracks/)


## Acknowledgements
- Mapping thanks to https://www.mapbox.com/mapbox-gl-js/api/ 
- Geojson conversion thanks to https://github.com/mapbox/togeojson 
- Applying RDP algorithm to tracks thanks to https://github.com/maxogden/simplify-geojson 
- Merging geojson features thanks to https://github.com/mapbox/geojson-merge 
