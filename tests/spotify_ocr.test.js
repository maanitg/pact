const assert = require('node:assert/strict');
const {
    cleanArtist,
    pairSpotifyLines,
    screenshotLayout,
    spotifyCropRegion,
} = require('../static/spotify-ocr.js');

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

assert.equal(screenshotLayout(1179, 2556), 'mobile');
assert.equal(screenshotLayout(1920, 1080), 'desktop');
const mobileCrop = spotifyCropRegion(1179, 2556);
const desktopCrop = spotifyCropRegion(1920, 1080);
assert.equal(mobileCrop.layout, 'mobile');
assert.equal(desktopCrop.layout, 'desktop');
assert.ok(mobileCrop.height > mobileCrop.width);
assert.ok(desktopCrop.width > desktopCrop.height * 0.75);

const desktopLines = [
    { text: '1', bbox: { x0: 8, x1: 18, y0: 40, y1: 60 } },
    { text: 'Snap Back', bbox: { x0: 80, x1: 260, y0: 38, y1: 61 } },
    { text: 'Paladin Strait', bbox: { x0: 680, x1: 850, y0: 40, y1: 62 } },
    { text: 'Twenty One Pilots', bbox: { x0: 82, x1: 280, y0: 68, y1: 88 } },
    { text: '2', bbox: { x0: 8, x1: 18, y0: 124, y1: 144 } },
    { text: 'Nights', bbox: { x0: 80, x1: 190, y0: 122, y1: 145 } },
    { text: 'Blonde', bbox: { x0: 680, x1: 770, y0: 124, y1: 146 } },
    { text: 'Frank Ocean', bbox: { x0: 82, x1: 220, y0: 152, y1: 172 } },
];
assert.deepEqual(pairSpotifyLines(desktopLines, 900, 1000), [
    'Snap Back — Twenty One Pilots',
    'Nights — Frank Ocean',
]);

console.log('Mobile and desktop Spotify OCR checks passed');
