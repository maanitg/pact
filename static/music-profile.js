(() => {
    const currentInput = document.querySelector('#current-images');
    if (!currentInput) return;

    const rewindInput = document.querySelector('#rewind-images');
    const confirmSection = document.querySelector('#scan-confirm-section');
    const scanButton = document.querySelector('#scan-button');
    const status = document.querySelector('#scan-status');
    const formError = document.querySelector('#form-error');
    const tagState = { scanForever: [], forever: [], current: [], wildcard: [] };
    const playlistState = { current: [], rewind: [] };
    let activeRoute = 'scan';

    const ignoredLines = new Set([
        'spotify', 'on repeat', 'repeat rewind', 'made for you', 'made for',
        'playlist', 'download', 'share', 'see all', 'back', 'more', 'play',
        'listening stats', 'top artists', 'top songs', 'top tracks',
        'title', '# title', 'album', 'date added', 'duration', 'your library'
    ]);

    async function showFiles(input, summarySelector, zoneSelector) {
        const count = input.files.length;
        const summary = document.querySelector(summarySelector);
        const zone = document.querySelector(zoneSelector);
        zone.classList.toggle('has-files', count === 2);
        if (count !== 2) {
            summary.textContent = `${count} of 2 selected`;
            return;
        }
        try {
            const layouts = await Promise.all(Array.from(input.files).map(async file => {
                const image = await loadImage(file);
                return window.SpotifyOcr.screenshotLayout(image.naturalWidth, image.naturalHeight);
            }));
            const layoutLabel = new Set(layouts).size === 1 ? layouts[0] : 'mixed mobile + desktop';
            summary.textContent = `2 of 2 ready · ${layoutLabel} detected`;
        } catch (_error) {
            summary.textContent = '2 of 2 ready';
        }
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

    function confirmedItems(key) {
        return uniqueLines(playlistState[key].map(item => item.trim()).filter(Boolean));
    }

    function updatePlaylistTotal(key) {
        const count = confirmedItems(key).length;
        document.querySelector(`#${key}-total`).textContent = `${count} item${count === 1 ? '' : 's'}`;
    }

    function renderPlaylistEditor(key) {
        const editor = document.querySelector(`#${key}-editor`);
        editor.replaceChildren();
        playlistState[key].forEach((value, index) => {
            const row = document.createElement('div');
            row.className = 'playlist-entry';

            const number = document.createElement('span');
            number.className = 'entry-number';
            number.textContent = String(index + 1).padStart(2, '0');

            const input = document.createElement('input');
            input.type = 'text';
            input.value = value;
            input.placeholder = 'Song — Artist';
            input.setAttribute('aria-label', `${key === 'current' ? 'On Repeat' : 'Repeat Rewind'} item ${index + 1}`);
            row.classList.toggle('needs-review', Boolean(value) && !value.includes(' — '));
            input.addEventListener('input', () => {
                playlistState[key][index] = input.value;
                row.classList.toggle('needs-review', Boolean(input.value) && !input.value.includes(' — '));
                updatePlaylistTotal(key);
            });

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'remove-entry';
            remove.textContent = '×';
            remove.setAttribute('aria-label', `Remove item ${index + 1}`);
            remove.addEventListener('click', () => {
                playlistState[key].splice(index, 1);
                renderPlaylistEditor(key);
            });

            row.append(number, input, remove);
            editor.appendChild(row);
        });
        updatePlaylistTotal(key);
    }

    function setPlaylistItems(key, items) {
        playlistState[key] = uniqueLines(items);
        renderPlaylistEditor(key);
    }

    document.querySelectorAll('.add-entry').forEach(button => {
        button.addEventListener('click', () => {
            const key = button.dataset.list;
            if (playlistState[key].length >= 20) return;
            playlistState[key].push('');
            renderPlaylistEditor(key);
            document.querySelector(`#${key}-editor .playlist-entry:last-child input`)?.focus();
        });
    });

    function cleanOcrLines(rawText) {
        return uniqueLines(rawText
            .split(/\r?\n/)
            .map(line => line.replace(/^\s*\d+[.)\s-]*/, '').replace(/[|©®]/g, '').trim())
            .map(line => line.replace(/\s+/g, ' '))
            .filter(line => line.length > 1 && line.length < 120)
            .filter(line => !ignoredLines.has(line.toLowerCase())));
    }

    function loadImage(file) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            const url = URL.createObjectURL(file);
            image.onload = () => {
                URL.revokeObjectURL(url);
                resolve(image);
            };
            image.onerror = () => {
                URL.revokeObjectURL(url);
                reject(new Error('Could not open screenshot.'));
            };
            image.src = url;
        });
    }

    async function prepareSpotifyCrop(file) {
        const image = await loadImage(file);
        const region = window.SpotifyOcr.spotifyCropRegion(image.naturalWidth, image.naturalHeight);
        const scale = Math.max(1, Math.min(2, 2200 / region.width, 2400 / region.height));
        const canvas = document.createElement('canvas');
        canvas.width = Math.round(region.width * scale);
        canvas.height = Math.round(region.height * scale);
        canvas.dataset.layout = region.layout;
        const context = canvas.getContext('2d', { willReadFrequently: true });
        context.drawImage(
            image,
            region.left,
            region.top,
            region.width,
            region.height,
            0,
            0,
            canvas.width,
            canvas.height
        );

        // Spotify uses white/gray text on a nearly black list. Grayscale plus a
        // contrast lift removes most artwork/UI color noise while retaining both lines.
        const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
        for (let offset = 0; offset < imageData.data.length; offset += 4) {
            const luminance = (0.299 * imageData.data[offset])
                + (0.587 * imageData.data[offset + 1])
                + (0.114 * imageData.data[offset + 2]);
            const value = Math.max(0, Math.min(255, (luminance - 35) * 1.45));
            imageData.data[offset] = value;
            imageData.data[offset + 1] = value;
            imageData.data[offset + 2] = value;
        }
        context.putImageData(imageData, 0, 0);
        return canvas;
    }

    async function recognizeFiles(worker, files, label) {
        const items = [];
        for (let index = 0; index < files.length; index += 1) {
            const crop = await prepareSpotifyCrop(files[index]);
            status.textContent = `Reading ${label} ${index + 1} of ${files.length} · ${crop.dataset.layout} layout…`;
            const result = await worker.recognize(crop, {}, { text: true, blocks: true });
            let detectedLines = window.SpotifyOcr.linesFromBlocks(result.data.blocks);
            if (!detectedLines.length) {
                detectedLines = cleanOcrLines(result.data.text).map((text, lineIndex) => ({
                    text,
                    bbox: { y0: lineIndex * 100, y1: (lineIndex * 100) + 30 }
                }));
            }
            items.push(...window.SpotifyOcr.pairSpotifyLines(detectedLines, crop.height, crop.width));
        }
        return uniqueLines(items);
    }

    function revealConfirmation() {
        confirmSection.classList.add('is-visible');
        confirmSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    scanButton.addEventListener('click', async () => {
        formError.textContent = '';
        const currentFiles = Array.from(currentInput.files);
        const rewindFiles = Array.from(rewindInput.files);
        if (currentFiles.length !== 2 || rewindFiles.length !== 2) {
            status.textContent = 'Choose exactly 2 screenshots from each playlist.';
            return;
        }
        if ([...currentFiles, ...rewindFiles].some(file => file.size > 15 * 1024 * 1024)) {
            status.textContent = 'One image is over 15 MB. Export a smaller PNG or JPG and try again.';
            return;
        }
        if (!window.Tesseract || !window.SpotifyOcr) {
            status.textContent = 'The private scanner could not load. Type the playlist names below instead.';
            revealConfirmation();
            return;
        }

        scanButton.disabled = true;
        document.querySelector('#scan-flow').setAttribute('aria-busy', 'true');
        let worker;
        try {
            worker = await window.Tesseract.createWorker('eng', 1, {
                logger: event => {
                    if (event.status === 'recognizing text') {
                        status.textContent = `Reading text… ${Math.round(event.progress * 100)}%`;
                    }
                }
            });
            await worker.setParameters({
                tessedit_pageseg_mode: '11',
                preserve_interword_spaces: '1',
                user_defined_dpi: '300'
            });
            setPlaylistItems('current', await recognizeFiles(worker, currentFiles, 'On Repeat'));
            setPlaylistItems('rewind', await recognizeFiles(worker, rewindFiles, 'Repeat Rewind'));
            status.textContent = 'Done. Check the names below—screenshots can be messy.';
        } catch (error) {
            console.error(error);
            status.textContent = 'We could not read those images. Type the playlist names below instead.';
        } finally {
            if (worker) await worker.terminate();
            scanButton.disabled = false;
            document.querySelector('#scan-flow').setAttribute('aria-busy', 'false');
            revealConfirmation();
        }
    });

    document.querySelector('#manual-scan-button').addEventListener('click', () => {
        if (!playlistState.current.length) {
            playlistState.current = ['', '', ''];
            renderPlaylistEditor('current');
        }
        if (!playlistState.rewind.length) {
            playlistState.rewind = ['', '', ''];
            renderPlaylistEditor('rewind');
        }
        revealConfirmation();
        document.querySelector('#current-editor input')?.focus();
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
            currentItems: confirmedItems('current'),
            rewindItems: confirmedItems('rewind'),
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
        setPlaylistItems('current', profile.current_items || profile.top_tracks || []);
        setPlaylistItems('rewind', profile.rewind_items || []);
        tagState.scanForever = [...(profile.forever_artists || profile.core_artists || [])].slice(0, 3);
        tagState.forever = [...(profile.forever_artists || profile.core_artists || [])].slice(0, 3);
        tagState.current = [...(profile.current_artists || [])].slice(0, 3);
        tagState.wildcard = [...(profile.wildcard_artists || [])].slice(0, 2);
        document.querySelectorAll('.tag-builder').forEach(renderTags);
        const taste = document.querySelector(`input[name="taste-mode"][value="${profile.taste_mode || 'balanced'}"]`);
        if (taste) taste.checked = true;
        if (mode === 'spotify_scan' && (playlistState.current.length || playlistState.rewind.length)) confirmSection.classList.add('is-visible');
    }

    hydrateExistingProfile();
})();
