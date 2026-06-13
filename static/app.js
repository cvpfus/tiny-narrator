const toggle = document.querySelector("#readerToggle");
const readerBar = document.querySelector(".reader-bar");
const modeStatus = document.querySelector("#modeStatus");
const currentStatus = document.querySelector("#currentStatus");
const runtimeStatus = document.querySelector("#runtimeStatus");
const modelStatus = document.querySelector("#modelStatus");
const readinessStatus = document.querySelector("#readinessStatus");
const imageStatus = document.querySelector("#imageStatus");
const voiceStatus = document.querySelector("#voiceStatus");
const latencyStatus = document.querySelector("#latencyStatus");
const liveNarration = document.querySelector("#liveNarration");
const audio = document.querySelector("#speechAudio");
const voiceControl = document.querySelector("#voiceControl");
const speedControl = document.querySelector("#speedControl");
const speedValue = document.querySelector("#speedValue");
const autoAdvanceControl = document.querySelector("#autoAdvanceControl");
const transcriptLog = document.querySelector("#transcriptLog");
const copyTranscriptButton = document.querySelector("#copyTranscriptButton");
const clearTranscriptButton = document.querySelector("#clearTranscriptButton");
const awardEvidenceList = document.querySelector("#awardEvidenceList");

const controls = {
  prev: document.querySelector("#prevButton"),
  play: document.querySelector("#playButton"),
  next: document.querySelector("#nextButton"),
  heading: document.querySelector("#headingButton"),
  image: document.querySelector("#imageButton"),
  summary: document.querySelector("#summaryButton"),
};

const nodes = [...document.querySelectorAll(".speakable")].map((element, index) => ({
  element,
  index,
  type: element.dataset.readerType || "paragraph",
  imageId: element.dataset.imageId || null,
  get text() {
    return element.innerText.replace(/\s+/g, " ").trim();
  },
}));

let enabled = false;
let currentIndex = -1;
let playing = false;
let requestSerial = 0;
let transcriptEntries = [];
let imageDescriptions = new Map();
let lastSpokenText = "";
let activeAutoAdvance = false;
let activeSpeechSerial = 0;

function updateSpeedValue() {
  speedValue.textContent = `${Number(speedControl.value).toFixed(2)}x`;
}

function formatElapsed(ms) {
  if (!Number.isFinite(ms)) {
    return "n/a";
  }
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function escapeHtml(value) {
  return value.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function renderTranscript() {
  transcriptLog.innerHTML = transcriptEntries
    .map((entry) => `
      <li>
        <div class="transcript-meta">
          <span>${escapeHtml(entry.type)} (${escapeHtml(formatElapsed(entry.elapsedMs))})</span>
          <span>${escapeHtml(entry.runtime)}</span>
        </div>
        <p class="transcript-text">${escapeHtml(entry.text)}</p>
      </li>
    `)
    .join("");
}

function addTranscriptEntry(entry) {
  transcriptEntries = [entry, ...transcriptEntries].slice(0, 12);
  renderTranscript();
}

function currentSection() {
  const activeNode = nodes[currentIndex]?.element;
  return activeNode?.closest("section") || document.querySelector("#article article");
}

function currentSectionPayload() {
  const section = currentSection();
  const title = section.querySelector("h1, h2, h3")?.innerText.trim() || "Article introduction";
  const text = [...section.querySelectorAll(".speakable")]
    .map((element) => element.innerText.replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join(" ");
  return { title, text };
}

async function loadManifest() {
  try {
    const manifest = await postJson("/api/article-manifest");
    const modelCount = Object.keys(manifest.models || {}).length;
    modelStatus.textContent = `${modelCount} tiny models, ${manifest.bonus_targets.join(", ")}`;
    const settings = manifest.reader_settings;
    if (settings?.voices?.length) {
      voiceControl.innerHTML = settings.voices
        .map((voice) => `<option value="${escapeHtml(voice.id)}">${escapeHtml(voice.label)}</option>`)
        .join("");
      voiceControl.value = settings.default_voice;
      voiceStatus.textContent = voiceControl.selectedOptions[0]?.textContent || "Ready";
    }
    if (settings?.speed) {
      speedControl.min = settings.speed.min;
      speedControl.max = settings.speed.max;
      speedControl.step = settings.speed.step;
      speedControl.value = settings.default_speed;
      updateSpeedValue();
    }
    autoAdvanceControl.checked = Boolean(settings?.default_auto_advance);
  } catch {
    modelStatus.textContent = "Manifest unavailable";
  }
}

async function loadAwardEvidence() {
  try {
    const payload = await postJson("/api/award-evidence");
    awardEvidenceList.innerHTML = payload.items
      .map((item) => `
        <li>
          <div class="award-title">
            <span>${escapeHtml(item.label)}</span>
            <span class="award-status">${escapeHtml(item.status)}</span>
          </div>
          <p class="award-evidence">${escapeHtml(item.evidence)}</p>
        </li>
      `)
      .join("");
  } catch {
    awardEvidenceList.innerHTML = `
      <li>
        <div class="award-title">
          <span>Checklist</span>
          <span class="award-status">offline</span>
        </div>
        <p class="award-evidence">Award evidence is unavailable.</p>
      </li>
    `;
  }
}

async function loadRuntimeStatus() {
  try {
    const payload = await postJson("/api/runtime-status");
    const brain = payload.reader_brain;
    const speech = payload.speech;
    const brainLabel = brain.available ? "llama.cpp online" : "llama.cpp fallback";
    const speechLabel = speech.available ? "Kokoro online" : "voice fallback";
    readinessStatus.textContent = `${brainLabel}, ${speechLabel}`;
  } catch {
    readinessStatus.textContent = "Fallback ready";
  }
}

async function loadImageDescriptions() {
  imageStatus.textContent = "Describing";
  try {
    const payload = await postJson("/api/image-descriptions");
    imageDescriptions = new Map(
      payload.descriptions.map((description) => [description.id, description]),
    );
    for (const node of nodes.filter((item) => item.type === "image")) {
      const description = imageDescriptions.get(node.imageId);
      const image = node.element.querySelector("img");
      if (description?.alt_text && image) {
        image.alt = description.alt_text;
        node.element.dataset.altReady = "true";
      }
    }
    imageStatus.textContent = `${imageDescriptions.size} ready`;
  } catch {
    imageStatus.textContent = "Fallback on demand";
  }
}

function setEnabled(nextValue) {
  enabled = nextValue;
  toggle.setAttribute("aria-pressed", String(enabled));
  toggle.lastChild.textContent = enabled ? " Screen reader on" : " Screen reader off";
  readerBar.hidden = !enabled;
  modeStatus.textContent = enabled ? "Reader on" : "Reader off";
  if (enabled) {
    announceIntro();
  } else {
    stopAudio();
    setActive(-1);
    liveNarration.textContent = "Turn on screen reader mode to begin.";
  }
}

function setActive(index) {
  nodes.forEach((node) => node.element.classList.remove("reader-active"));
  currentIndex = index;
  const node = nodes[currentIndex];
  if (!node) {
    currentStatus.textContent = "No item selected";
    return;
  }
  node.element.classList.add("reader-active");
  node.element.setAttribute("tabindex", "-1");
  node.element.focus({ preventScroll: true });
  node.element.scrollIntoView({ block: "center", behavior: "smooth" });
  currentStatus.textContent = `${node.type}, item ${currentIndex + 1} of ${nodes.length}`;
}

function stopAudio() {
  audio.pause();
  audio.removeAttribute("src");
  window.speechSynthesis?.cancel();
  activeAutoAdvance = false;
  activeSpeechSerial = 0;
  playing = false;
  controls.play.textContent = "Play";
}

function maybeAutoAdvance(serial) {
  if (!enabled || !autoAdvanceControl.checked || !activeAutoAdvance || serial !== requestSerial) {
    return;
  }
  const nextIndex = currentIndex + 1;
  if (nextIndex < nodes.length) {
    window.setTimeout(() => narrate(nextIndex), 250);
  } else {
    liveNarration.textContent = "End of article.";
    activeAutoAdvance = false;
  }
}

function browserSpeak(text, serial) {
  if (!("speechSynthesis" in window)) {
    return false;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = Number(speedControl.value);
  utterance.onend = () => {
    playing = false;
    controls.play.textContent = "Play";
    maybeAutoAdvance(serial);
  };
  window.speechSynthesis.speak(utterance);
  playing = true;
  controls.play.textContent = "Pause";
  return true;
}

async function speakNarration(text, serial, autoAdvance = false) {
  lastSpokenText = text;
  activeAutoAdvance = autoAdvance;
  activeSpeechSerial = serial;
  const speech = await postJson("/api/speak", {
    text,
    voice: voiceControl.value || "af_heart",
    speed: Number(speedControl.value),
  });

  if (serial !== requestSerial) return;

  if (speech.runtime === "fallback") {
    const spoke = browserSpeak(text, serial);
    voiceStatus.textContent = spoke ? "Browser fallback" : "Transcript only";
    if (!spoke) {
      liveNarration.textContent = `${text} Audio fallback is unavailable. Transcript is visible.`;
    }
    return speech;
  }

  if (speech.audio_url) {
    audio.src = speech.audio_url;
    await audio.play().catch(() => {
      const spoke = browserSpeak(text, serial);
      voiceStatus.textContent = spoke ? "Browser fallback" : "Audio ready";
      liveNarration.textContent = spoke ? text : `${text} Audio is ready. Press Play to hear it.`;
    });
    playing = !audio.paused || window.speechSynthesis?.speaking;
    controls.play.textContent = playing ? "Pause" : "Play";
    if (!window.speechSynthesis?.speaking) {
      voiceStatus.textContent = speech.runtime;
    }
  }
  return speech;
}

async function postJson(url, payload) {
  const options = payload === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  };
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function narrate(index) {
  if (!enabled || !nodes[index]) return;
  const serial = ++requestSerial;
  setActive(index);
  const node = nodes[index];
  runtimeStatus.textContent = "Thinking";
  controls.play.disabled = true;

  try {
    let sourceText = node.text;
    if (node.type === "image") {
      let description = imageDescriptions.get(node.imageId);
      if (!description) {
        description = await postJson("/api/describe-image", {
          image_id: node.imageId,
          caption: node.text,
        });
      }
      sourceText = description.alt_text;
    }

    const result = await postJson("/api/reader-brain", {
      node_type: node.type,
      text: sourceText,
      position: `item ${index + 1} of ${nodes.length}`,
      mode: "narrate",
    });

    if (serial !== requestSerial) return;

    runtimeStatus.textContent = result.runtime;
    liveNarration.textContent = result.narration;

    const speech = await speakNarration(result.narration, serial, true);
    const elapsedMs = (result.elapsed_ms || 0) + (speech?.elapsed_ms || 0);
    latencyStatus.textContent = formatElapsed(elapsedMs);
    addTranscriptEntry({
      type: node.type,
      runtime: `${result.runtime}/${speech?.runtime || "voice"}`,
      text: result.narration,
      elapsedMs,
    });
  } catch (error) {
    runtimeStatus.textContent = "Error";
    liveNarration.textContent = `Narration failed: ${error.message}`;
  } finally {
    controls.play.disabled = false;
  }
}

async function summarizeCurrentSection() {
  if (!enabled) return;
  const serial = ++requestSerial;
  const section = currentSectionPayload();
  runtimeStatus.textContent = "Summarizing";
  controls.summary.disabled = true;

  try {
    const result = await postJson("/api/reader-brain", {
      node_type: "section",
      text: section.text,
      position: section.title,
      mode: "summarize",
    });

    if (serial !== requestSerial) return;

    runtimeStatus.textContent = result.runtime;
    liveNarration.textContent = result.narration;

    const speech = await speakNarration(result.narration, serial, false);
    const elapsedMs = (result.elapsed_ms || 0) + (speech?.elapsed_ms || 0);
    latencyStatus.textContent = formatElapsed(elapsedMs);
    addTranscriptEntry({
      type: "summary",
      runtime: `${result.runtime}/${speech?.runtime || "voice"}`,
      text: result.narration,
      elapsedMs,
    });
  } catch (error) {
    runtimeStatus.textContent = "Error";
    liveNarration.textContent = `Summary failed: ${error.message}`;
  } finally {
    controls.summary.disabled = false;
  }
}

function announceIntro() {
  const headings = nodes.filter((node) => node.type === "heading").length;
  const images = nodes.filter((node) => node.type === "image").length;
  liveNarration.textContent =
    `Screen reader mode on. Article contains ${headings} headings, ${images} images, and ${nodes.length} readable items. Press N for next, H for heading, I for image, S for section summary, or Space to begin.`;
  runtimeStatus.textContent = "Ready";
}

function nextByType(type) {
  const start = Math.max(currentIndex + 1, 0);
  const found = nodes.find((node) => node.index >= start && node.type === type);
  if (found) return narrate(found.index);
  const wrapped = nodes.find((node) => node.type === type);
  if (wrapped) return narrate(wrapped.index);
}

toggle.addEventListener("click", () => setEnabled(!enabled));
controls.next.addEventListener("click", () => narrate(Math.min(currentIndex + 1, nodes.length - 1)));
controls.prev.addEventListener("click", () => narrate(Math.max(currentIndex - 1, 0)));
controls.heading.addEventListener("click", () => nextByType("heading"));
controls.image.addEventListener("click", () => nextByType("image"));
controls.summary.addEventListener("click", () => summarizeCurrentSection());
voiceControl.addEventListener("change", () => {
  voiceStatus.textContent = voiceControl.selectedOptions[0]?.textContent || "Custom voice";
});
speedControl.addEventListener("input", () => {
  updateSpeedValue();
});
copyTranscriptButton.addEventListener("click", async () => {
  const text = transcriptEntries
    .slice()
    .reverse()
    .map((entry) => `[${entry.type} / ${entry.runtime}] ${entry.text}`)
    .join("\n");
  await navigator.clipboard?.writeText(text);
  liveNarration.textContent = text ? "Transcript copied." : "Transcript is empty.";
});
clearTranscriptButton.addEventListener("click", () => {
  transcriptEntries = [];
  renderTranscript();
  liveNarration.textContent = "Transcript cleared.";
});
controls.play.addEventListener("click", () => {
  if (!enabled) return;
  if (currentIndex < 0) {
    narrate(0);
    return;
  }
  if (playing) {
    audio.pause();
    window.speechSynthesis?.pause();
    playing = false;
    controls.play.textContent = "Play";
  } else if (window.speechSynthesis?.paused) {
    window.speechSynthesis.resume();
    playing = true;
    controls.play.textContent = "Pause";
  } else if (audio.src) {
    audio.play();
    playing = true;
    controls.play.textContent = "Pause";
  } else if (lastSpokenText) {
    activeAutoAdvance = false;
    browserSpeak(lastSpokenText, requestSerial);
  } else {
    narrate(currentIndex);
  }
});

loadManifest();
loadAwardEvidence();
loadRuntimeStatus();
loadImageDescriptions();
updateSpeedValue();

audio.addEventListener("ended", () => {
  playing = false;
  controls.play.textContent = "Play";
  maybeAutoAdvance(activeSpeechSerial);
});

document.addEventListener("keydown", (event) => {
  if (!enabled) return;
  const key = event.key.toLowerCase();
  if ([" ", "n", "p", "h", "i", "s", "r", "escape"].includes(key)) {
    event.preventDefault();
  }
  if (key === " ") controls.play.click();
  if (key === "n") controls.next.click();
  if (key === "p") controls.prev.click();
  if (key === "h") controls.heading.click();
  if (key === "i") controls.image.click();
  if (key === "s") controls.summary.click();
  if (key === "r" && currentIndex >= 0) narrate(currentIndex);
  if (key === "escape") {
    stopAudio();
    liveNarration.textContent = "Reading stopped.";
  }
});
