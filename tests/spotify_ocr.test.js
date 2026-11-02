const assert = require('node:assert/strict');
const { cleanArtist, pairSpotifyLines } = require('../static/spotify-ocr.js');

assert.equal(cleanArtist('BY 3 Video - Twenty One Pilots'), 'Twenty One Pilots');
assert.equal(cleanArtist('E Childish Gambino'), 'Childish Gambino');

const lines = [
    { text: '. Snap Back PY .', bbox: { y0: 40, y1: 70 } },
    { text: 'BY 3 Video - Twenty One Pilots', bbox: { y0: 76, y1: 98 } },
    { text: 'II. Earth: The Oldest Computer', bbox: { y0: 155, y1: 185 } },
    { text: 'E Childish Gambino, Azealia Banks', bbox: { y0: 191, y1: 213 } },
];

assert.deepEqual(pairSpotifyLines(lines, 1000), [
    'Snap Back — Twenty One Pilots',
    'II. Earth: The Oldest Computer — Childish Gambino, Azealia Banks',
]);

console.log('Spotify OCR parser checks passed');
