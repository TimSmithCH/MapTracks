# MapTracks
[![Build Status](https://travis-ci.org/TimSmithCH/MapTracks.svg?branch=master)](https://travis-ci.org/TimSmithCH/MapTracks)

Layout tracks of outings on a map

Step 1: Upload gpx files of outings to [TimSmithCH/MapTracks/tracks/gpx](https://github.com/TimSmithCH/MapTracks/tree/master/tracks/gpx) 
Step 2: Travis build gets triggered 
 - Converts gpx files to geojson 
 - Drops the timing info on tracks for privacy/efficieny 
 - Applies [Ramer-Douglas-Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm) to simplify the tracks for overviewing 
 - Merges all simlified tracks in a single overview view 
Step 3: View overview [here](https://timsmithch.github.io/MapTracks/) 

## Acknowledgements
- Mapping thanks to https://www.mapbox.com/mapbox-gl-js/api/ 
- Geojson conversion thanks to https://github.com/mapbox/togeojson 
- Applying RDP algorithm to tracks thanks to https://github.com/maxogden/simplify-geojson 
- Merging geojson features thanks to https://github.com/mapbox/geojson-merge 
