var test = require('tape').test,
    assert = require('assert'),
    glob = require('glob'),
    fs = require('fs'),
    tj = require('@mapbox/togeojson');

if (!process.browser) {
    var xmldom = require('xmldom');
}
var simplify = require('simplify-geojson')

function kmlFixtureEqual(t, file) {
    var outfile = file.substr(0, file.lastIndexOf(".")) + ".geojson";
    outfile = outfile.replace(/\/kml\//, '/geojson/')
    if (process.env.UPDATE) {
        var output = tj.kml(toDOM(fs.readFileSync(file)));
        fs.writeFileSync(outfile, JSON.stringify(output, null, 4));
    }
    t.equal(
        JSON.stringify(tj.kml(toDOM(fs.readFileSync(file))), null, 4),
        fs.readFileSync(outfile, 'utf8'),
        file);
}

function gpxFixtureEqual(t, file) {
    var outfile = file.substr(0, file.lastIndexOf(".")) + ".geojson";
    var simplefile = file.substr(0, file.lastIndexOf(".")) + "_simple.geojson";
    outfile = outfile.replace(/\/gpx\//, '/geojson/')
    simplefile = simplefile.replace(/\/gpx\//, '/geojson/')
    console.log('read: ',file);
    if (process.env.UPDATE) {
        var output = tj.gpx(toDOM(fs.readFileSync(file)));
        // Drop all time information for privacy reasons, and unnecessary for route finding!
        delete output.features[0].properties.coordTimes;
        // Write out human readable GeoJson
        fs.writeFileSync(outfile, JSON.stringify(output, null, 4));
        console.log('update: ',outfile);
        // Apply Ramer–Douglas–Peucker line simplification to smooth line and shrink file
        var simplified = simplify(output,0.0005);   // Epsilon equivalent to 56m separation
        fs.writeFileSync(simplefile, JSON.stringify(simplified, null, 4));
    }

    tcomp = tj.gpx(toDOM(fs.readFileSync(file, 'utf8'))),
    delete tcomp.features[0].properties.coordTimes;
    t.deepEqual(tcomp, JSON.parse(fs.readFileSync(outfile, 'utf8')), file);
}

test('KML', function(t) {
    glob.sync('tracks/kml/*/*.kml').forEach(function(file) {
        kmlFixtureEqual(t, file);
    });
    t.end();
});

test('GPX', function(t) {
    glob.sync('tracks/gpx/*/*.gpx').forEach(function(file) {
        gpxFixtureEqual(t, file);
    });
    t.end();
});

function toDOM(_) {
    if (typeof DOMParser === 'undefined') {
        return (new xmldom.DOMParser()).parseFromString(_.toString());
    } else {
        return (new DOMParser()).parseFromString(_, 'text/xml');
    }
}
