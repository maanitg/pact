(function exposeSpotifyOcr(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SpotifyOcr = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
    const ignored = new Set([
        'spotify', 'on repeat', 'repeat rewind', 'made for you', 'made for',
        'playlist', 'download', 'share', 'see all', 'back', 'more', 'play'
    ]);

    function normalizeText(value) {
        return String(value || '')
            .replace(/[|©®]/g, '')
            .replace(/\s+/g, ' ')
            .trim();
    }

    function cleanTitle(value) {
        return normalizeText(value)
            .replace(/^[^\p{L}\p{N}(]+/u, '')
            .replace(/\s+(?:PY|BY)\s*[.·•]*$/u, '')
            .replace(/\s+[.·•]+$/u, '')
            .replace(/[^\p{L}\p{N})!?'.…-]+$/u, '')
            .trim();
    }

    function cleanArtist(value) {
        let cleaned = normalizeText(value);
        // Spotify places download, explicit, and video badges before the artist.
        // OCR often turns those icons into short junk such as "BY 3 Video -".
        cleaned = cleaned.replace(/^.{0,14}\bVideo\b\s*[•·.\-–—]*\s*/i, '');
        cleaned = cleaned.replace(/^(?:E|EXPLICIT)\s+[•·.\-–—]*\s*/i, '');
        cleaned = cleaned.replace(/^[^\p{L}\p{N}]+/u, '');
        cleaned = cleaned.replace(/[^\p{L}\p{N})!?'.…-]+$/u, '');
        return cleaned.trim();
    }

    function linesFromBlocks(blocks) {
        const lines = [];
        (blocks || []).forEach(block => {
            (block.paragraphs || []).forEach(paragraph => {
                (paragraph.lines || []).forEach(line => {
                    const text = normalizeText(line.text);
                    if (text) lines.push({ text, bbox: line.bbox || {} });
                });
            });
        });
        return lines;
    }

    function centerY(line, fallback) {
        const y0 = Number(line.bbox?.y0);
        const y1 = Number(line.bbox?.y1);
        return Number.isFinite(y0) && Number.isFinite(y1) ? (y0 + y1) / 2 : fallback;
    }

    function pairSpotifyLines(rawLines, cropHeight) {
        const lines = rawLines
            .map((line, index) => ({ ...line, text: normalizeText(line.text), y: centerY(line, index * 100) }))
            .filter(line => line.text.length > 1)
            .filter(line => !ignored.has(line.text.toLowerCase()))
            .filter(line => /[\p{L}\p{N}]/u.test(line.text))
            .sort((left, right) => left.y - right.y);

        const paired = [];
        const pairGap = Math.max(48, Number(cropHeight || 0) * 0.06);
        for (let index = 0; index < lines.length; index += 1) {
            const title = cleanTitle(lines[index].text);
            const next = lines[index + 1];
            const artist = next ? cleanArtist(next.text) : '';
            const closeEnough = next && (next.y - lines[index].y) > 0 && (next.y - lines[index].y) <= pairGap;

            if (title && artist && closeEnough) {
                paired.push(`${title} — ${artist}`);
                index += 1;
            } else if (title.length > 2) {
                paired.push(title);
            }
        }

        const seen = new Set();
        return paired.filter(item => {
            const key = item.toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });
    }

    return { cleanArtist, cleanTitle, linesFromBlocks, pairSpotifyLines };
});
