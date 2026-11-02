(() => {
    const artistsInput = document.querySelector('#artists-image');
    const tracksInput = document.querySelector('#tracks-image');
    const artistsText = document.querySelector('#top-artists');
    const tracksText = document.querySelector('#top-tracks');
    const confirmSection = document.querySelector('#confirm-section');
    const scanButton = document.querySelector('#scan-button');
    const status = document.querySelector('#scan-status');
    const formError = document.querySelector('#form-error');

    if (!artistsInput) return;

    const ignoredLines = new Set([
        'spotify', 'listening stats', 'top artists', 'top songs', 'top tracks',
        'artists', 'songs', 'share', 'see all', 'your listening stats',
        'last 4 weeks', 'past 4 weeks', 'back'
    ]);

    function previewFile(input, previewId, zoneId) {
        const preview = document.querySelector(previewId);
        const zone = document.querySelector(zoneId);
        const file = input.files[0];
        if (!file) return;
        preview.src = URL.createObjectURL(file);
        preview.style.display = 'block';
        zone.classList.add('has-image');
    }

    artistsInput.addEventListener('change', () => previewFile(artistsInput, '#artists-preview', '#artists-zone'));
    tracksInput.addEventListener('change', () => previewFile(tracksInput, '#tracks-preview', '#tracks-zone'));

    function cleanOcrLines(rawText) {
        const seen = new Set();
        return rawText
            .split(/\r?\n/)
            .map(line => line.replace(/^\s*\d+[.)\s-]*/, '').replace(/[|©®]/g, '').trim())
            .map(line => line.replace(/\s+/g, ' '))
            .filter(line => line.length > 1 && line.length < 100)
            .filter(line => !ignoredLines.has(line.toLowerCase()))
            .filter(line => {
                const key = line.toLowerCase();
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
            })
            .slice(0, 20);
    }

    async function recognize(worker, file, label) {
        status.textContent = `Reading ${label}…`;
        const result = await worker.recognize(file);
        return cleanOcrLines(result.data.text);
    }

    scanButton.addEventListener('click', async () => {
        formError.textContent = '';
        if (!artistsInput.files[0] && !tracksInput.files[0]) {
            status.textContent = 'Choose at least one screenshot first.';
            return;
        }
        if (!window.Tesseract) {
            status.textContent = 'The private scanner could not load. You can still enter the lists manually.';
            confirmSection.classList.add('is-visible');
            return;
        }

        scanButton.disabled = true;
        let worker;
        try {
            worker = await window.Tesseract.createWorker('eng', 1, {
                logger: event => {
                    if (event.status === 'recognizing text') {
                        status.textContent = `Reading text… ${Math.round(event.progress * 100)}%`;
                    }
                }
            });
            if (artistsInput.files[0]) {
                artistsText.value = (await recognize(worker, artistsInput.files[0], 'your artists')).join('\n');
            }
            if (tracksInput.files[0]) {
                tracksText.value = (await recognize(worker, tracksInput.files[0], 'your songs')).join('\n');
            }
            status.textContent = 'Done. Check the names below—screenshots can be messy.';
        } catch (error) {
            console.error(error);
            status.textContent = 'We could not read that image. Enter the names manually below.';
        } finally {
            if (worker) await worker.terminate();
            scanButton.disabled = false;
            confirmSection.classList.add('is-visible');
            confirmSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });

    document.querySelector('#manual-button').addEventListener('click', () => {
        confirmSection.classList.add('is-visible');
        confirmSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        artistsText.focus();
    });

    function linesFrom(value) {
        return value.split(/\r?\n/).map(item => item.trim()).filter(Boolean);
    }

    document.querySelector('#save-profile').addEventListener('click', async () => {
        formError.textContent = '';
        const payload = {
            topArtists: linesFrom(artistsText.value),
            topTracks: linesFrom(tracksText.value),
            coreArtists: document.querySelector('#core-artists').value.split(',').map(item => item.trim()).filter(Boolean),
            tasteMode: document.querySelector('input[name="taste-mode"]:checked')?.value || 'balanced'
        };
        if (!payload.topArtists.length && !payload.topTracks.length) {
            formError.textContent = 'Add at least one artist or song first.';
            return;
        }

        const button = document.querySelector('#save-profile');
        button.disabled = true;
        button.textContent = 'Printing your receipt…';
        try {
            const response = await fetch('/api/music-profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.message || 'Could not save your profile.');
            window.location.assign(result.redirectUrl);
        } catch (error) {
            formError.textContent = error.message;
            button.disabled = false;
            button.textContent = 'Make my music receipt';
        }
    });

    if (artistsText.value.trim() || tracksText.value.trim()) {
        confirmSection.classList.add('is-visible');
    }
})();
