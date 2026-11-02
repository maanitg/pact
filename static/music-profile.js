(() => {
    const currentInput = document.querySelector('#current-images');
    if (!currentInput) return;

    const rewindInput = document.querySelector('#rewind-images');
    const currentText = document.querySelector('#current-items');
    const rewindText = document.querySelector('#rewind-items');
    const confirmSection = document.querySelector('#scan-confirm-section');
    const scanButton = document.querySelector('#scan-button');
    const status = document.querySelector('#scan-status');
    const formError = document.querySelector('#form-error');
    const tagState = { scanForever: [], forever: [], current: [], wildcard: [] };
    let activeRoute = 'scan';

    const ignoredLines = new Set([
        'spotify', 'on repeat', 'repeat rewind', 'made for you', 'made for',
        'playlist', 'download', 'share', 'see all', 'back', 'more', 'play',
        'listening stats', 'top artists', 'top songs', 'top tracks'
    ]);

    function showFiles(input, summarySelector, zoneSelector) {
        const files = Array.from(input.files).slice(0, 3);
        document.querySelector(summarySelector).textContent = files.length
            ? `${files.length} screenshot${files.length === 1 ? '' : 's'} ready`
            : '';
        document.querySelector(zoneSelector).classList.toggle('has-files', files.length > 0);
    }

    currentInput.addEventListener('change', () => showFiles(currentInput, '#current-summary', '#current-zone'));
    rewindInput.addEventListener('change', () => showFiles(rewindInput, '#rewind-summary', '#rewind-zone'));

    function uniqueLines(lines) {
        const seen = new Set();
        return lines.filter(line => {
            const key = line.toLowerCase();
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        }).slice(0, 20);
    }

    function cleanOcrLines(rawText) {
        return uniqueLines(rawText
            .split(/\r?\n/)
            .map(line => line.replace(/^\s*\d+[.)\s-]*/, '').replace(/[|©®]/g, '').trim())
            .map(line => line.replace(/\s+/g, ' '))
            .filter(line => line.length > 1 && line.length < 120)
            .filter(line => !ignoredLines.has(line.toLowerCase())));
    }

    async function recognizeFiles(worker, files, label) {
        const lines = [];
        for (let index = 0; index < files.length; index += 1) {
            status.textContent = `Reading ${label} screenshot ${index + 1} of ${files.length}…`;
            const result = await worker.recognize(files[index]);
            lines.push(...cleanOcrLines(result.data.text));
        }
        return uniqueLines(lines);
    }

    function revealConfirmation() {
        confirmSection.classList.add('is-visible');
        confirmSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    scanButton.addEventListener('click', async () => {
        formError.textContent = '';
        const currentFiles = Array.from(currentInput.files).slice(0, 3);
        const rewindFiles = Array.from(rewindInput.files).slice(0, 3);
        if (!currentFiles.length || !rewindFiles.length) {
            status.textContent = 'Choose at least one screenshot from each playlist.';
            return;
        }
        if (!window.Tesseract) {
            status.textContent = 'The private scanner could not load. Type the playlist names below instead.';
            revealConfirmation();
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
            currentText.value = (await recognizeFiles(worker, currentFiles, 'On Repeat')).join('\n');
            rewindText.value = (await recognizeFiles(worker, rewindFiles, 'Repeat Rewind')).join('\n');
            status.textContent = 'Done. Check the names below—screenshots can be messy.';
        } catch (error) {
            console.error(error);
            status.textContent = 'We could not read those images. Type the playlist names below instead.';
        } finally {
            if (worker) await worker.terminate();
            scanButton.disabled = false;
            revealConfirmation();
        }
    });

    document.querySelector('#manual-scan-button').addEventListener('click', () => {
        revealConfirmation();
        currentText.focus();
    });

    document.querySelectorAll('.route-choice').forEach(button => {
        button.addEventListener('click', () => {
            activeRoute = button.dataset.route;
            document.querySelectorAll('.route-choice').forEach(choice => {
                const selected = choice === button;
                choice.classList.toggle('is-active', selected);
                choice.setAttribute('aria-pressed', String(selected));
            });
            document.querySelector('#scan-flow').hidden = activeRoute !== 'scan';
            document.querySelector('#picker-flow').hidden = activeRoute !== 'picker';
            document.querySelector('#final-step-number').textContent = activeRoute === 'scan' ? '5' : '3';
            formError.textContent = '';
        });
    });

    function renderTags(builder) {
        const key = builder.dataset.tagKey;
        const limit = Number(builder.dataset.limit);
        const list = builder.querySelector('.tag-list');
        list.replaceChildren();
        tagState[key].forEach((artist, index) => {
            const tag = document.createElement('button');
            tag.type = 'button';
            tag.className = 'artist-tag';
            tag.textContent = `${artist} ×`;
            tag.setAttribute('aria-label', `Remove ${artist}`);
            tag.addEventListener('click', () => {
                tagState[key].splice(index, 1);
                renderTags(builder);
            });
            list.appendChild(tag);
        });
        builder.querySelector('.tag-count').textContent = `${tagState[key].length} / ${limit}`;
        builder.classList.toggle('is-complete', tagState[key].length === limit);
        builder.querySelector('input').disabled = tagState[key].length >= limit;
        builder.querySelector('.tag-add').disabled = tagState[key].length >= limit;
    }

    function addTag(builder) {
        const key = builder.dataset.tagKey;
        const limit = Number(builder.dataset.limit);
        const input = builder.querySelector('input');
        const artist = input.value.replace(/\s+/g, ' ').trim().replace(/^,|,$/g, '');
        if (!artist || tagState[key].length >= limit) return;
        if (tagState[key].some(item => item.toLowerCase() === artist.toLowerCase())) {
            input.value = '';
            return;
        }
        tagState[key].push(artist.slice(0, 120));
        input.value = '';
        renderTags(builder);
        if (!input.disabled) input.focus();
    }

    document.querySelectorAll('.tag-builder').forEach(builder => {
        builder.querySelector('.tag-add').addEventListener('click', () => addTag(builder));
        builder.querySelector('input').addEventListener('keydown', event => {
            if (event.key === 'Enter' || event.key === ',') {
                event.preventDefault();
                addTag(builder);
            }
        });
        renderTags(builder);
    });

    function linesFrom(value) {
        return uniqueLines(value.split(/\r?\n/).map(item => item.trim()).filter(Boolean));
    }

    function validatePayload(payload) {
        if (payload.captureMode === 'spotify_scan') {
            if (payload.currentItems.length < 3 || payload.rewindItems.length < 3) {
                return 'Keep at least 3 items from both On Repeat and Repeat Rewind.';
            }
            if (payload.foreverArtists.length !== 3) return 'Add exactly 3 forever artists.';
            return '';
        }
        if (payload.foreverArtists.length !== 3 || payload.currentArtists.length !== 3 || payload.wildcardArtists.length !== 2) {
            return 'Complete all 8 artist picks: 3 forever, 3 current, and 2 wildcard.';
        }
        return '';
    }

    document.querySelector('#save-profile').addEventListener('click', async () => {
        formError.textContent = '';
        const payload = {
            captureMode: activeRoute === 'scan' ? 'spotify_scan' : 'artist_picker',
            currentItems: linesFrom(currentText.value),
            rewindItems: linesFrom(rewindText.value),
            foreverArtists: activeRoute === 'scan' ? tagState.scanForever : tagState.forever,
            currentArtists: activeRoute === 'picker' ? tagState.current : [],
            wildcardArtists: activeRoute === 'picker' ? tagState.wildcard : [],
            tasteMode: document.querySelector('input[name="taste-mode"]:checked')?.value || 'balanced'
        };
        const validationMessage = validatePayload(payload);
        if (validationMessage) {
            formError.textContent = validationMessage;
            return;
        }

        const button = document.querySelector('#save-profile');
        button.disabled = true;
        button.textContent = 'Printing your receipt…';
        try {
            const response = await fetch('/api/music-profile', {
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
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

    function hydrateExistingProfile() {
        let profile;
        try {
            profile = JSON.parse(document.querySelector('#existing-profile').textContent);
        } catch (_error) {
            return;
        }
        if (!profile) return;
        const mode = profile.capture_mode || (profile.source === 'artist_picker' ? 'artist_picker' : 'spotify_scan');
        activeRoute = mode;
        document.querySelector(`.route-choice[data-route="${mode === 'artist_picker' ? 'picker' : 'scan'}"]`).click();
        currentText.value = (profile.current_items || profile.top_tracks || []).join('\n');
        rewindText.value = (profile.rewind_items || []).join('\n');
        tagState.scanForever = [...(profile.forever_artists || profile.core_artists || [])].slice(0, 3);
        tagState.forever = [...(profile.forever_artists || profile.core_artists || [])].slice(0, 3);
        tagState.current = [...(profile.current_artists || [])].slice(0, 3);
        tagState.wildcard = [...(profile.wildcard_artists || [])].slice(0, 2);
        document.querySelectorAll('.tag-builder').forEach(renderTags);
        const taste = document.querySelector(`input[name="taste-mode"][value="${profile.taste_mode || 'balanced'}"]`);
        if (taste) taste.checked = true;
        if (mode === 'spotify_scan' && (currentText.value || rewindText.value)) confirmSection.classList.add('is-visible');
    }

    hydrateExistingProfile();
})();
