var test = require('tape').test,
    assert = require('assert'),
    glob = require('glob'),
    fs = require('fs'),
    tj = require('@mapbox/togeojson');

if (!process.browser) {
    var xmldom = require('xmldom');
}

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
    outfile = outfile.replace(/\/gpx\//, '/geojson/')
    console.log('read: ',file);
    if (process.env.UPDATE) {
        var output = tj.gpx(toDOM(fs.readFileSync(file)));
        fs.writeFileSync(outfile, JSON.stringify(output, null, 4));
        console.log('update: ',outfile);
    }

    t.deepEqual(
        tj.gpx(toDOM(fs.readFileSync(file, 'utf8'))),
        JSON.parse(fs.readFileSync(outfile, 'utf8')),
        file);
}

test('KML', function(t) {
    glob.sync('tracks/kml/*.kml').forEach(function(file) {
        kmlFixtureEqual(t, file);
    });
    t.end();
});

test('GPX', function(t) {
    glob.sync('tracks/gpx/*.gpx').forEach(function(file) {
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
