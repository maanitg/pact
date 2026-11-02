(function exposeSpotifyOcr(root, factory) {
    const api = factory();
    if (typeof module === 'object' && module.exports) module.exports = api;
    root.SpotifyOcr = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, () => {
    const ignored = new Set([
        'spotify', 'on repeat', 'repeat rewind', 'made for you', 'made for',
        'playlist', 'download', 'share', 'see all', 'back', 'more', 'play',
        'title', '# title', 'album', 'date added', 'duration', 'your library',
        'home', 'search', 'create', 'liked songs', 'install app', 'queue'
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

    function leftX(line) {
        const x0 = Number(line.bbox?.x0);
        return Number.isFinite(x0) ? x0 : null;
    }

    function lineHeight(line) {
        const y0 = Number(line.bbox?.y0);
        const y1 = Number(line.bbox?.y1);
        return Number.isFinite(y0) && Number.isFinite(y1) ? Math.max(1, y1 - y0) : 24;
    }

    function screenshotLayout(width, height) {
        return Number(width) / Math.max(1, Number(height)) >= 1.08 ? 'desktop' : 'mobile';
    }

    function spotifyCropRegion(width, height) {
        const layout = screenshotLayout(width, height);
        const ratios = layout === 'desktop'
            // Desktop: isolate the title/artist column and leave album/date/duration out.
            ? { left: 0.13, top: 0.16, width: 0.39, height: 0.72 }
            // Mobile: remove artwork, controls, the player, and bottom navigation.
            : { left: 0.16, top: 0.12, width: 0.68, height: 0.70 };
        return {
            layout,
            left: Math.round(width * ratios.left),
            top: Math.round(height * ratios.top),
            width: Math.max(1, Math.round(width * ratios.width)),
            height: Math.max(1, Math.round(height * ratios.height)),
        };
    }

    function pairSpotifyLines(rawLines, cropHeight, cropWidth) {
        let lines = rawLines
            .map((line, index) => ({ ...line, text: normalizeText(line.text), y: centerY(line, index * 100) }))
            .filter(line => line.text.length > 1)
            .filter(line => !ignored.has(line.text.toLowerCase()))
            .filter(line => !/^\s*\d{1,3}\s*$/.test(line.text))
            .filter(line => /[\p{L}\p{N}]/u.test(line.text))
            .sort((left, right) => left.y - right.y || (leftX(left) || 0) - (leftX(right) || 0));

        // Desktop OCR can still glimpse the Album column. Spotify's title and
        // artist lines share the left-most text column, so discard distant columns.
        const xValues = lines.map(leftX).filter(value => value !== null).sort((a, b) => a - b);
        if (xValues.length >= 4 && cropWidth) {
            const leftColumn = xValues[Math.floor(xValues.length * 0.2)];
            const columnWidth = Math.max(120, Number(cropWidth) * 0.22);
            lines = lines.filter(line => leftX(line) === null || leftX(line) <= leftColumn + columnWidth);
        }

        const paired = [];
        const heights = lines.map(lineHeight).sort((a, b) => a - b);
        const medianHeight = heights.length ? heights[Math.floor(heights.length / 2)] : 24;
        const pairGap = Math.max(44, Math.min(Number(cropHeight || 1000) * 0.045, medianHeight * 3.2));
        const alignmentTolerance = Math.max(42, Number(cropWidth || 800) * 0.07);
        for (let index = 0; index < lines.length; index += 1) {
            const title = cleanTitle(lines[index].text);
            const next = lines[index + 1];
            const artist = next ? cleanArtist(next.text) : '';
            const titleX = leftX(lines[index]);
            const artistX = next ? leftX(next) : null;
            const aligned = titleX === null || artistX === null || Math.abs(titleX - artistX) <= alignmentTolerance;
            const closeEnough = next
                && (next.y - lines[index].y) > Math.max(2, medianHeight * 0.15)
                && (next.y - lines[index].y) <= pairGap
                && aligned;

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

    return {
        cleanArtist,
        cleanTitle,
        linesFromBlocks,
        pairSpotifyLines,
        screenshotLayout,
        spotifyCropRegion,
    };
});
