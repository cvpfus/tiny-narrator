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
const demoScriptStatus = document.querySelector("#demoScriptStatus");
const demoScriptList = document.querySelector("#demoScriptList");
const demoApiCheckList = document.querySelector("#demoApiCheckList");
const awardEvidenceList = document.querySelector("#awardEvidenceList");
const submissionReadinessStatus = document.querySelector("#submissionReadinessStatus");
const submissionReadinessList = document.querySelector("#submissionReadinessList");
const copyEvidenceButton = document.querySelector("#copyEvidenceButton");
const budgetStatus = document.querySelector("#budgetStatus");
const modelBudgetList = document.querySelector("#modelBudgetList");
const runtimeSetupStatus = document.querySelector("#runtimeSetupStatus");
const runtimeSetupList = document.querySelector("#runtimeSetupList");
const imageReceiptStatus = document.querySelector("#imageReceiptStatus");
const imageReceiptList = document.querySelector("#imageReceiptList");

const controls = {
  prev: document.querySelector("#prevButton"),
  play: document.querySelector("#playButton"),
  next: document.querySelector("#nextButton"),
  heading: document.querySelector("#headingButton"),
  image: document.querySelector("#imageButton"),
  summary: document.querySelector("#summaryButton"),
  stop: document.querySelector("#stopButton"),
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

nodes.forEach((node) => {
  if (!node.element.id) {
    node.element.id = `reader-node-${node.index + 1}`;
  }
  node.element.dataset.readerPosition = String(node.index + 1);
});
readerBar.setAttribute("aria-controls", nodes.map((node) => node.element.id).join(" "));

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

function readerTypeLabel(type) {
  return {
    heading: "Heading",
    image: "Image",
    paragraph: "Paragraph",
    quote: "Quote",
    section: "Section",
  }[type] || roleLabel(type);
}

function readerItemStatus(node) {
  return `${readerTypeLabel(node.type)}, item ${node.index + 1} of ${nodes.length}`;
}

function initialReaderIndex() {
  if (!nodes.length) {
    return -1;
  }

  const focusedNode = nodes.find((node) => node.element.contains(document.activeElement));
  if (focusedNode) {
    return focusedNode.index;
  }

  const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
  const visibleNodes = nodes
    .map((node) => {
      const rect = node.element.getBoundingClientRect();
      const inView = rect.bottom > 0 && rect.top < viewportHeight;
      return {
        node,
        score: inView ? Math.abs(rect.top - viewportHeight * 0.25) : Number.POSITIVE_INFINITY,
      };
    })
    .filter((item) => Number.isFinite(item.score));

  return visibleNodes.reduce(
    (best, item) => (item.score < best.score ? item : best),
    { node: nodes[0], score: Number.POSITIVE_INFINITY },
  ).node.index;
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

async function loadDemoScript() {
  try {
    const payload = await postJson("/api/demo-script");
    demoScriptStatus.textContent = `${payload.estimated_minutes} min`;
    demoScriptList.innerHTML = payload.actions
      .map((item) => `
        <li>
          <div class="demo-script-title">
            <span>${escapeHtml(item.label)}</span>
            <span>${escapeHtml(`Step ${item.step}`)}</span>
          </div>
          <p>${escapeHtml(item.action)}</p>
          <p>${escapeHtml(item.evidence)}</p>
        </li>
      `)
      .join("");
    demoApiCheckList.innerHTML = payload.api_checks
      .map((item) => `
        <li>
          <span>${escapeHtml(item.method)}</span>
          <code>${escapeHtml(item.path)}</code>
          <p>${escapeHtml(item.expect)}${item.sample_body ? " Sample body included." : ""}</p>
          <code class="demo-api-command">${escapeHtml(item.curl)}</code>
          <code class="demo-api-command">${escapeHtml(item.powershell)}</code>
        </li>
      `)
      .join("");
  } catch {
    demoScriptStatus.textContent = "Unavailable";
    demoScriptList.innerHTML = `
      <li>
        <div class="demo-script-title">
          <span>Judge runbook</span>
          <span>offline</span>
        </div>
        <p>The structured demo script is unavailable.</p>
      </li>
    `;
    demoApiCheckList.innerHTML = "";
  }
}

async function loadSubmissionReadiness() {
  try {
    const payload = await postJson("/api/submission-readiness");
    submissionReadinessStatus.textContent = payload.all_passed
      ? `${payload.passed_checks}/${payload.total_checks} pass`
      : "Review needed";
    submissionReadinessList.innerHTML = payload.checks
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
    submissionReadinessStatus.textContent = "Unavailable";
    submissionReadinessList.innerHTML = `
      <li>
        <div class="award-title">
          <span>Submission readiness</span>
          <span class="award-status">offline</span>
        </div>
        <p class="award-evidence">Submission readiness evidence is unavailable.</p>
      </li>
    `;
  }
}

function roleLabel(role) {
  return role
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

async function loadModelBudget() {
  try {
    const payload = await postJson("/api/model-budget");
    budgetStatus.textContent = payload.all_models_within_limit
      ? `All <= ${payload.limit_billion}B`
      : "Review needed";
    modelBudgetList.innerHTML = payload.models
      .map((model) => `
        <li>
          <div class="budget-row">
            <span>${escapeHtml(roleLabel(model.role))}</span>
            <span class="budget-pill">${escapeHtml(model.params)}</span>
          </div>
          <p>${escapeHtml(model.id)}</p>
        </li>
      `)
      .join("");
  } catch {
    budgetStatus.textContent = "Unavailable";
    modelBudgetList.innerHTML = `
      <li>
        <div class="budget-row">
          <span>Model budget</span>
          <span class="budget-pill">offline</span>
        </div>
        <p>Tiny Titan evidence is unavailable.</p>
      </li>
    `;
  }
}

async function loadRuntimeSetup() {
  try {
    const payload = await postJson("/api/runtime-setup");
    runtimeSetupStatus.textContent = `${payload.steps.length} paths`;
    runtimeSetupList.innerHTML = payload.steps
      .map((step) => `
        <li>
          <div class="runtime-row">
            <span>${escapeHtml(step.label)}</span>
            <span class="runtime-pill">${escapeHtml(step.runtime)}</span>
          </div>
          <p>${escapeHtml(step.fallback)}</p>
        </li>
      `)
      .join("");
  } catch {
    runtimeSetupStatus.textContent = "Unavailable";
    runtimeSetupList.innerHTML = `
      <li>
        <div class="runtime-row">
          <span>Runtime plan</span>
          <span class="runtime-pill">offline</span>
        </div>
        <p>Setup evidence is unavailable.</p>
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
    imageReceiptStatus.textContent = `${payload.descriptions.length} receipts`;
    imageReceiptList.innerHTML = payload.descriptions
      .map((description) => `
        <li>
          <div class="image-receipt-row">
            <span>${escapeHtml(description.id)}</span>
            <span class="image-receipt-pill">${escapeHtml(description.generation_status)}</span>
          </div>
          <p>${escapeHtml(description.generation_model)} | seed ${escapeHtml(String(description.seed))}</p>
          <p>${escapeHtml(description.prompt)}</p>
        </li>
      `)
      .join("");
  } catch {
    imageStatus.textContent = "Fallback on demand";
    imageReceiptStatus.textContent = "Unavailable";
    imageReceiptList.innerHTML = `
      <li>
        <div class="image-receipt-row">
          <span>Image receipts</span>
          <span class="image-receipt-pill">offline</span>
        </div>
        <p>Generated image provenance is unavailable.</p>
      </li>
    `;
  }
}

function setEnabled(nextValue) {
  enabled = nextValue;
  toggle.setAttribute("aria-pressed", String(enabled));
  toggle.lastChild.textContent = enabled ? " Screen reader on" : " Screen reader off";
  readerBar.hidden = !enabled;
  modeStatus.textContent = enabled ? "Reader on" : "Reader off";
  if (enabled) {
    if (currentIndex < 0) {
      setActive(initialReaderIndex());
    }
    announceIntro();
  } else {
    stopAudio();
    setActive(-1);
    liveNarration.textContent = "Turn on screen reader mode to begin.";
  }
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

function stopAudio() {
  haltPlayback();
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
  haltPlayback({ clearAutoAdvance: false });
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
  haltPlayback({ clearAutoAdvance: false });
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
  const currentItem = nodes[currentIndex] ? ` Current item: ${readerItemStatus(nodes[currentIndex]).toLowerCase()}.` : "";
  liveNarration.textContent =
    `Screen reader mode on. Article contains ${headings} headings, ${images} images, and ${nodes.length} readable items.${currentItem} Press N for next, H for heading, I for image, S for section summary, or Space to begin.`;
  runtimeStatus.textContent = "Ready";
}

function nextByType(type) {
  const start = Math.max(currentIndex + 1, 0);
  const found = nodes.find((node) => node.index >= start && node.type === type);
  if (found) return narrate(found.index);
  const wrapped = nodes.find((node) => node.type === type);
  if (wrapped) return narrate(wrapped.index);
  liveNarration.textContent = `No ${readerTypeLabel(type).toLowerCase()} items in this article.`;
}

toggle.addEventListener("click", () => setEnabled(!enabled));
controls.next.addEventListener("click", () => narrate(Math.min(currentIndex + 1, nodes.length - 1)));
controls.prev.addEventListener("click", () => narrate(Math.max(currentIndex - 1, 0)));
controls.heading.addEventListener("click", () => nextByType("heading"));
controls.image.addEventListener("click", () => nextByType("image"));
controls.summary.addEventListener("click", () => summarizeCurrentSection());
controls.stop.addEventListener("click", () => {
  stopAudio();
  liveNarration.textContent = "Reading stopped.";
});
nodes.forEach((node) => {
  node.element.addEventListener("click", (event) => {
    if (!enabled || isControlTarget(event.target)) return;
    narrate(node.index);
  });
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
copyEvidenceButton.addEventListener("click", async () => {
  try {
    const payload = await postJson("/api/evidence-bundle");
    const text = JSON.stringify(payload, null, 2);
    if (!navigator.clipboard) {
      liveNarration.textContent = "Evidence bundle loaded, but clipboard access is unavailable.";
      return;
    }
    await navigator.clipboard.writeText(text);
    liveNarration.textContent = "Evidence bundle copied.";
  } catch (error) {
    liveNarration.textContent = `Evidence bundle failed: ${error.message}`;
  }
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
loadDemoScript();
loadAwardEvidence();
loadSubmissionReadiness();
loadModelBudget();
loadRuntimeSetup();
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
  if (key === "r" && currentIndex >= 0) narrate(currentIndex);
  if (key === "escape") controls.stop.click();
});
