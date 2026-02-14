/**
 * Internship Logger – Frontend Application
 *
 * Handles audio recording via MediaRecorder API, supports multiple
 * recordings per entry, and communicates with the FastAPI backend.
 */

// ── DOM Elements ─────────────────────────────────────────────────────────

const recordBtn = document.getElementById('recordBtn');
const recordIcon = recordBtn.querySelector('.record-icon');
const clipsList = document.getElementById('clipsList');
const clipActions = document.getElementById('clipActions');
const addMoreBtn = document.getElementById('addMoreBtn');
const sendBtn = document.getElementById('sendBtn');
const statusDot = document.getElementById('statusDot');
const statusText = document.getElementById('statusText');
const notionLink = document.getElementById('notionLink');
const errorMessage = document.getElementById('errorMessage');
const newRecordingBtn = document.getElementById('newRecordingBtn');
const retryBtn = document.getElementById('retryBtn');
const transcriptBox = document.getElementById('transcriptBox');
const transcriptText = document.getElementById('transcriptText');

const screens = {
    record: document.getElementById('screen-record'),
    done: document.getElementById('screen-done'),
    error: document.getElementById('screen-error'),
};

// ── State ────────────────────────────────────────────────────────────────

let mediaRecorder = null;
let audioChunks = [];
let audioStream = null;
let isRecording = false;
let recognition = null;
let finalTranscript = '';

// Array of recorded clips: { blob, url }
let clips = [];

// ── Screen Management ────────────────────────────────────────────────────

function showScreen(name) {
    Object.values(screens).forEach(s => s.classList.remove('active'));
    screens[name].classList.add('active');
}

function setStatus(text, state = '') {
    statusText.textContent = text;
    statusDot.className = 'status-dot' + (state ? ` ${state}` : '');
}

// ── Speech Recognition (Live Transcript) ────────────────────────────────

function startSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('Web Speech API not supported in this browser');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

    const langSelect = document.getElementById('langSelect');
    recognition.lang = langSelect ? langSelect.value : 'en-US';

    finalTranscript = '';

    recognition.onresult = (event) => {
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const text = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += text + ' ';
            } else {
                interim += text;
            }
        }
        transcriptText.innerHTML =
            (finalTranscript || '') +
            (interim ? `<span class="interim">${interim}</span>` : '');
        transcriptText.style.fontStyle = 'normal';
        transcriptBox.scrollTop = transcriptBox.scrollHeight;
    };

    recognition.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
    };

    recognition.onend = () => {
        if (isRecording && recognition) {
            try { recognition.start(); } catch (e) { }
        }
    };

    recognition.start();
    transcriptBox.classList.remove('hidden');
    transcriptText.innerHTML = '<span class="interim">Listening...</span>';
}

function stopSpeechRecognition() {
    if (recognition) {
        recognition.onend = null;
        recognition.stop();
        recognition = null;
    }
}

// ── Clips UI ─────────────────────────────────────────────────────────────

function renderClips() {
    clipsList.innerHTML = '';
    clips.forEach((clip, index) => {
        const card = document.createElement('div');
        card.className = 'clip-card';
        card.innerHTML = `
            <span class="clip-label">#${index + 1}</span>
            <audio src="${clip.url}" controls></audio>
            <button class="clip-remove" data-index="${index}" aria-label="Remove clip">✕</button>
        `;
        clipsList.appendChild(card);
    });

    if (clips.length > 0) {
        clipsList.classList.remove('hidden');
        clipActions.classList.remove('hidden');
    } else {
        clipsList.classList.add('hidden');
        clipActions.classList.add('hidden');
    }
}

function removeClip(index) {
    URL.revokeObjectURL(clips[index].url);
    clips.splice(index, 1);
    renderClips();
    if (clips.length === 0) {
        showRecordButton();
    }
}

clipsList.addEventListener('click', (e) => {
    const btn = e.target.closest('.clip-remove');
    if (btn) {
        removeClip(parseInt(btn.dataset.index, 10));
    }
});

// ── Recording ────────────────────────────────────────────────────────────

// Detect the best supported audio MIME type for MediaRecorder
function getSupportedMimeType() {
    const types = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/mp4',
        'audio/ogg;codecs=opus',
        'audio/ogg',
    ];
    for (const type of types) {
        if (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(type)) {
            return type;
        }
    }
    return ''; // let the browser pick its default
}

function mimeToSuffix(mime) {
    if (mime.startsWith('audio/webm')) return '.webm';
    if (mime.startsWith('audio/mp4')) return '.mp4';
    if (mime.startsWith('audio/ogg')) return '.ogg';
    return '.webm'; // fallback
}

function showRecordButton() {
    recordBtn.parentElement.style.display = 'flex';
    document.querySelector('.record-prompt').style.display = 'block';
}

function hideRecordButton() {
    recordBtn.parentElement.style.display = 'none';
    document.querySelector('.record-prompt').style.display = 'none';
}

async function startRecording() {
    try {
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });

        const mimeType = getSupportedMimeType();
        const recorderOptions = mimeType ? { mimeType } : undefined;
        mediaRecorder = new MediaRecorder(audioStream, recorderOptions);

        const chosenMime = mediaRecorder.mimeType || mimeType || 'audio/webm';
        audioChunks = [];

        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: chosenMime });
            const url = URL.createObjectURL(blob);
            clips.push({ blob, url, suffix: mimeToSuffix(chosenMime) });
            renderClips();
            hideRecordButton();
            setStatus(`${clips.length} clip${clips.length > 1 ? 's' : ''} recorded`, '');
        };

        mediaRecorder.start();
        isRecording = true;
        recordBtn.classList.add('recording');
        recordBtn.setAttribute('aria-label', 'Stop recording');
        recordIcon.textContent = '■';
        setStatus('Recording...', 'recording');
        startSpeechRecognition();
    } catch (err) {
        setStatus('Microphone access denied', 'error');
        console.error('Microphone error:', err);
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    if (audioStream) {
        audioStream.getTracks().forEach(t => t.stop());
    }
    stopSpeechRecognition();
    transcriptBox.classList.add('hidden');
    isRecording = false;
    recordBtn.classList.remove('recording');
    recordBtn.setAttribute('aria-label', 'Start recording');
    recordIcon.textContent = '●';
}

function addMore() {
    // Show the record button again for another recording
    showRecordButton();
    setStatus('Idle', '');
}

function resetAll() {
    clips.forEach(c => URL.revokeObjectURL(c.url));
    clips = [];
    audioChunks = [];
    clipsList.innerHTML = '';
    clipsList.classList.add('hidden');
    clipActions.classList.add('hidden');
    showRecordButton();
    setStatus('Idle', '');
    sendBtn.disabled = false;
    sendBtn.textContent = '📤 Send to Notion';
    transcriptBox.classList.add('hidden');
    transcriptText.innerHTML = 'Listening...';
    finalTranscript = '';
}

// ── Send to Notion ───────────────────────────────────────────────────────

async function blobToBase64(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    return btoa(
        new Uint8Array(arrayBuffer)
            .reduce((data, byte) => data + String.fromCharCode(byte), '')
    );
}

function pollJobStatus(jobId) {
    const STATUS_MESSAGES = {
        pending: 'Queued – waiting for AI worker...',
        processing: 'AI is processing your recording...',
        done: 'Saved to Notion!',
        error: 'Something went wrong',
    };

    const interval = setInterval(async () => {
        try {
            const resp = await fetch(`/api/jobs/${jobId}/status`);
            const data = await resp.json();

            const statusMsg = STATUS_MESSAGES[data.status] || data.status;
            setStatus(statusMsg, data.status === 'pending' ? 'processing' : data.status);

            if (data.status === 'done') {
                clearInterval(interval);
                if (data.notion_url) {
                    notionLink.innerHTML = `<a href="${data.notion_url}" target="_blank">Open in Notion</a>`;
                } else {
                    notionLink.textContent = '';
                }
                showScreen('done');
            } else if (data.status === 'error') {
                clearInterval(interval);
                errorMessage.textContent = data.error_message || 'Processing failed';
                showScreen('error');
            }
        } catch (err) {
            // Network glitch – keep polling
            console.warn('Poll error:', err);
        }
    }, 3000);
}

async function sendToNotion() {
    if (clips.length === 0) return;

    sendBtn.disabled = true;
    sendBtn.textContent = 'Submitting...';
    addMoreBtn.disabled = true;
    setStatus('Uploading audio...', 'processing');

    try {
        // Convert all clips to base64
        const audioClips = [];
        for (const clip of clips) {
            const b64 = await blobToBase64(clip.blob);
            audioClips.push({ audio_b64: b64, suffix: clip.suffix || '.webm' });
        }

        const response = await fetch('/api/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ clips: audioClips }),
        });

        const result = await response.json();

        if (result.job_id) {
            setStatus('Queued – waiting for AI worker...', 'processing');
            pollJobStatus(result.job_id);
        } else {
            setStatus('Error', 'error');
            errorMessage.textContent = result.detail || 'Submission failed';
            showScreen('error');
        }
    } catch (err) {
        setStatus('Error', 'error');
        errorMessage.textContent = `Network error: ${err.message}`;
        showScreen('error');
    } finally {
        addMoreBtn.disabled = false;
    }
}

// ── Event Listeners ──────────────────────────────────────────────────────

recordBtn.addEventListener('click', () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});

addMoreBtn.addEventListener('click', addMore);
sendBtn.addEventListener('click', sendToNotion);

newRecordingBtn.addEventListener('click', () => {
    resetAll();
    showScreen('record');
});

retryBtn.addEventListener('click', () => {
    resetAll();
    showScreen('record');
});

// Update language dynamically if changed during recording
const langSelect = document.getElementById('langSelect');
if (langSelect) {
    langSelect.addEventListener('change', () => {
        if (recognition) {
            recognition.lang = langSelect.value;
            recognition.stop();
        }
    });
}
