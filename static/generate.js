const form = document.querySelector("#articleGeneratorForm");
const topicInput = document.querySelector("#topicInput");
const generateArticleButton = document.querySelector("#generateArticleButton");
const generatorStatus = document.querySelector("#generatorStatus");
const generatedKicker = document.querySelector("#generatedKicker");
const generatedTitle = document.querySelector("#generatedTitle");
const generatedDek = document.querySelector("#generatedDek");
const generatedSections = document.querySelector("#generatedSections");
const generatedThumbnail = document.querySelector("#generatedThumbnail");
const thumbnailReceipt = document.querySelector("#thumbnailReceipt");
const toggle = document.querySelector("#readerToggle");
const readerBar = document.querySelector(".reader-bar");
const modeStatus = document.querySelector("#modeStatus");
const currentStatus = document.querySelector("#currentStatus");
const runtimeStatus = document.querySelector("#runtimeStatus");
const voiceStatus = document.querySelector("#voiceStatus");
const latencyStatus = document.querySelector("#latencyStatus");
const liveNarration = document.querySelector("#liveNarration");
const transcriptLog = document.querySelector("#transcriptLog");
const copyTranscriptButton = document.querySelector("#copyTranscriptButton");
const clearTranscriptButton = document.querySelector("#clearTranscriptButton");
const audio = document.querySelector("#speechAudio");
const voiceControl = document.querySelector("#voiceControl");
const speedControl = document.querySelector("#speedControl");
const speedValue = document.querySelector("#speedValue");
const autoAdvanceControl = document.querySelector("#autoAdvanceControl");

const controls = {
  prev: document.querySelector("#prevButton"),
  play: document.querySelector("#playButton"),
  next: document.querySelector("#nextButton"),
  heading: document.querySelector("#headingButton"),
  image: document.querySelector("#imageButton"),
  summary: document.querySelector("#summaryButton"),
  repeat: document.querySelector("#repeatButton"),
  stop: document.querySelector("#stopButton"),
};

let nodes = [];
let enabled = false;
let currentIndex = -1;
let playing = false;
let requestSerial = 0;
let transcriptEntries = [];
let lastSpokenText = "";
let activeAutoAdvance = false;
let activeSpeechSerial = 0;

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function formatElapsed(ms) {
  if (!Number.isFinite(ms)) {
    return "n/a";
  }
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(2)} s`;
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

function readerTypeLabel(type) {
  return {
    heading: "Heading",
    image: "Image",
    paragraph: "Paragraph",
    section: "Section",
  }[type] || type;
}

function readableText(element) {
  if (element.dataset.readerType === "image") {
    const image = element.querySelector("img");
    const caption = element.querySelector("figcaption");
    return [image?.alt, caption?.innerText]
      .filter(Boolean)
      .join(" ")
      .replace(/\s+/g, " ")
      .trim();
  }
  return element.innerText.replace(/\s+/g, " ").trim();
}

function refreshReaderNodes() {
  nodes = [...document.querySelectorAll("#generatedArticle .speakable")].map((element, index) => ({
    element,
    index,
    type: element.dataset.readerType || "paragraph",
    get text() {
      return readableText(element);
    },
  }));
  nodes.forEach((node) => {
    if (!node.element.id) {
      node.element.id = `generated-reader-node-${node.index + 1}`;
    }
    node.element.dataset.readerPosition = String(node.index + 1);
  });
  readerBar.setAttribute("aria-controls", nodes.map((node) => node.element.id).join(" "));
  if (currentIndex >= nodes.length) {
    currentIndex = nodes.length - 1;
  }
}

function readerItemStatus(node) {
  return `${readerTypeLabel(node.type)}, item ${node.index + 1} of ${nodes.length}`;
}

function updateSpeedValue() {
  speedValue.textContent = `${Number(speedControl.value).toFixed(2)}x`;
}

function renderTranscript() {
  transcriptLog.innerHTML = transcriptEntries
    .map((entry) => `
      <li>
        <div class="transcript-meta">
          <span>${escapeHtml(entry.type)} (${escapeHtml(formatElapsed(entry.elapsedMs))})</span>
          <span>${escapeHtml(entry.runtime)}</span>
        </div>
        <p class="transcript-position">${escapeHtml(entry.position)}</p>
        <p class="transcript-text">${escapeHtml(entry.text)}</p>
      </li>
    `)
    .join("");
}

function addTranscriptEntry(entry) {
  transcriptEntries = [entry, ...transcriptEntries].slice(0, 12);
  renderTranscript();
}

async function copyTextToClipboard(text, successMessage, emptyMessage, unavailableMessage) {
  if (!text) {
    liveNarration.textContent = emptyMessage;
    return false;
  }
  if (!navigator.clipboard) {
    liveNarration.textContent = unavailableMessage;
    return false;
  }
  await navigator.clipboard.writeText(text);
  liveNarration.textContent = successMessage;
  return true;
}

function isControlTarget(target) {
  return target instanceof Element
    && Boolean(target.closest("input, select, textarea, button, a, [contenteditable='true']"));
}

function shouldHandleReaderShortcut(event) {
  if (event.key === "Escape") {
    return true;
  }
  return !isControlTarget(event.target);
}

function setActive(index) {
  nodes.forEach((node) => {
    node.element.classList.remove("reader-active");
    node.element.removeAttribute("aria-current");
    node.element.removeAttribute("tabindex");
  });
  currentIndex = index;
  const node = nodes[currentIndex];
  if (!node) {
    currentStatus.textContent = "No item selected";
    return;
  }
  node.element.classList.add("reader-active");
  node.element.setAttribute("aria-current", "true");
  node.element.setAttribute("tabindex", "-1");
  node.element.focus({ preventScroll: true });
  node.element.scrollIntoView({ block: "center", behavior: "smooth" });
  currentStatus.textContent = readerItemStatus(node);
}

function haltPlayback({ clearAutoAdvance = true } = {}) {
  audio.pause();
  audio.removeAttribute("src");
  window.speechSynthesis?.cancel();
  if (clearAutoAdvance) {
    activeAutoAdvance = false;
  }
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
    liveNarration.textContent = "End of generated article.";
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

async function narrate(index) {
  if (!enabled || !nodes[index]) return;
  const serial = ++requestSerial;
  haltPlayback({ clearAutoAdvance: false });
  setActive(index);
  const node = nodes[index];
  runtimeStatus.textContent = "Thinking";
  controls.play.disabled = true;

  try {
    const result = await postJson("/api/reader-brain", {
      node_type: node.type,
      text: node.text,
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
      position: readerItemStatus(node),
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

function articleSummaryText() {
  return nodes.map((node) => node.text).filter(Boolean).join(" ");
}

async function summarizeGeneratedArticle() {
  if (!enabled) return;
  const serial = ++requestSerial;
  haltPlayback({ clearAutoAdvance: false });
  runtimeStatus.textContent = "Summarizing";
  controls.summary.disabled = true;

  try {
    const result = await postJson("/api/reader-brain", {
      node_type: "section",
      text: articleSummaryText(),
      position: generatedTitle.textContent,
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
      position: generatedTitle.textContent,
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
  refreshReaderNodes();
  const headings = nodes.filter((node) => node.type === "heading").length;
  const images = nodes.filter((node) => node.type === "image").length;
  const currentItem = nodes[currentIndex] ? ` Current item: ${readerItemStatus(nodes[currentIndex]).toLowerCase()}.` : "";
  liveNarration.textContent =
    `Screen reader mode on. Generated article contains ${headings} headings, ${images} images, and ${nodes.length} readable items.${currentItem} Press N for next, H for heading, I for image, S for summary, or Space to begin.`;
  runtimeStatus.textContent = "Ready";
}

function setEnabled(nextValue) {
  enabled = nextValue;
  toggle.setAttribute("aria-pressed", String(enabled));
  toggle.lastChild.textContent = enabled ? " Screen reader on" : " Screen reader off";
  readerBar.hidden = !enabled;
  modeStatus.textContent = enabled ? "Reader on" : "Reader off";
  if (enabled) {
    refreshReaderNodes();
    if (currentIndex < 0) {
      setActive(0);
    }
    announceIntro();
  } else {
    haltPlayback();
    setActive(-1);
    liveNarration.textContent = "Generate an article, then turn on screen reader mode.";
  }
}

function nextByType(type) {
  const start = Math.max(currentIndex + 1, 0);
  const found = nodes.find((node) => node.index >= start && node.type === type);
  if (found) return narrate(found.index);
  const wrapped = nodes.find((node) => node.type === type);
  if (wrapped) return narrate(wrapped.index);
  liveNarration.textContent = `No ${readerTypeLabel(type).toLowerCase()} items in this generated article.`;
}

function repeatCurrentItem() {
  if (currentIndex >= 0) {
    narrate(currentIndex);
  } else {
    liveNarration.textContent = "No reader item selected.";
  }
}

function renderArticle(payload) {
  const article = payload.article;
  const thumbnail = payload.thumbnail;
  generatedKicker.textContent = `${payload.runtime} article`;
  generatedTitle.textContent = article.title;
  generatedDek.textContent = article.dek;
  generatedThumbnail.src = thumbnail.image_url;
  generatedThumbnail.alt = `Generated thumbnail for ${payload.topic}.`;
  thumbnailReceipt.textContent =
    `${thumbnail.generation_model} | seed ${thumbnail.seed} | ${thumbnail.runtime}`;
  generatedSections.innerHTML = article.sections
    .map((section) => `
      <section>
        <h2 class="speakable" data-reader-type="heading">${escapeHtml(section.heading)}</h2>
        <p class="speakable" data-reader-type="paragraph">${escapeHtml(section.body)}</p>
      </section>
    `)
    .join("");
  generatorStatus.textContent =
    `Generated with ${payload.model}; thumbnail from ${thumbnail.generation_model}; ${formatElapsed(payload.elapsed_ms)}.`;
  refreshReaderNodes();
  if (enabled) {
    setActive(0);
    announceIntro();
  }
}

async function loadManifest() {
  try {
    const manifest = await postJson("/api/article-manifest");
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
    voiceStatus.textContent = "Manifest unavailable";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const topic = topicInput.value.trim();
  if (!topic) {
    generatorStatus.textContent = "Enter a topic first.";
    return;
  }

  generateArticleButton.disabled = true;
  generatorStatus.textContent = "Generating article and Klein thumbnail.";
  try {
    const payload = await postJson("/api/generate-article", { topic });
    renderArticle(payload);
  } catch (error) {
    generatorStatus.textContent = `Generation failed: ${error.message}`;
  } finally {
    generateArticleButton.disabled = false;
  }
});

toggle.addEventListener("click", () => setEnabled(!enabled));
controls.next.addEventListener("click", () => narrate(Math.min(currentIndex + 1, nodes.length - 1)));
controls.prev.addEventListener("click", () => narrate(Math.max(currentIndex - 1, 0)));
controls.heading.addEventListener("click", () => nextByType("heading"));
controls.image.addEventListener("click", () => nextByType("image"));
controls.summary.addEventListener("click", () => summarizeGeneratedArticle());
controls.repeat.addEventListener("click", () => repeatCurrentItem());
controls.stop.addEventListener("click", () => {
  haltPlayback();
  liveNarration.textContent = "Reading stopped.";
});
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
    .map((entry) => `[${entry.type} / ${entry.position} / ${entry.runtime}] ${entry.text}`)
    .join("\n");
  await copyTextToClipboard(
    text,
    "Transcript copied.",
    "Transcript is empty.",
    "Transcript is visible, but clipboard access is unavailable.",
  );
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
audio.addEventListener("ended", () => {
  playing = false;
  controls.play.textContent = "Play";
  maybeAutoAdvance(activeSpeechSerial);
});
document.addEventListener("keydown", (event) => {
  if (!enabled) return;
  if (!shouldHandleReaderShortcut(event)) return;
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
  if (key === "r") controls.repeat.click();
  if (key === "escape") controls.stop.click();
});

loadManifest();
refreshReaderNodes();
updateSpeedValue();
