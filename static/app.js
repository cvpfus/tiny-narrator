const toggle = document.querySelector("#readerToggle");
const readerBar = document.querySelector(".reader-bar");
const modeStatus = document.querySelector("#modeStatus");
const currentStatus = document.querySelector("#currentStatus");
const runtimeStatus = document.querySelector("#runtimeStatus");
const liveNarration = document.querySelector("#liveNarration");
const audio = document.querySelector("#speechAudio");
const speedControl = document.querySelector("#speedControl");

const controls = {
  prev: document.querySelector("#prevButton"),
  play: document.querySelector("#playButton"),
  next: document.querySelector("#nextButton"),
  heading: document.querySelector("#headingButton"),
  image: document.querySelector("#imageButton"),
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
  playing = false;
  controls.play.textContent = "Play";
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function narrate(index) {
  if (!enabled || !nodes[index]) return;
  setActive(index);
  const node = nodes[index];
  runtimeStatus.textContent = "Thinking";

  let sourceText = node.text;
  if (node.type === "image") {
    const description = await postJson("/api/describe-image", {
      image_id: node.imageId,
      caption: node.text,
    });
    sourceText = description.alt_text;
  }

  const result = await postJson("/api/reader-brain", {
    node_type: node.type,
    text: sourceText,
    position: `item ${index + 1} of ${nodes.length}`,
    mode: "narrate",
  });

  runtimeStatus.textContent = result.runtime;
  liveNarration.textContent = result.narration;

  const speech = await postJson("/api/speak", {
    text: result.narration,
    speed: Number(speedControl.value),
  });

  if (speech.audio_url) {
    audio.src = speech.audio_url;
    await audio.play().catch(() => {});
    playing = true;
    controls.play.textContent = "Pause";
  }
}

function announceIntro() {
  const headings = nodes.filter((node) => node.type === "heading").length;
  const images = nodes.filter((node) => node.type === "image").length;
  liveNarration.textContent =
    `Screen reader mode on. Article contains ${headings} headings, ${images} images, and ${nodes.length} readable items. Press N for next, H for heading, I for image, or Space to begin.`;
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
controls.play.addEventListener("click", () => {
  if (!enabled) return;
  if (currentIndex < 0) {
    narrate(0);
    return;
  }
  if (playing) {
    audio.pause();
    playing = false;
    controls.play.textContent = "Play";
  } else if (audio.src) {
    audio.play();
    playing = true;
    controls.play.textContent = "Pause";
  } else {
    narrate(currentIndex);
  }
});

audio.addEventListener("ended", () => {
  playing = false;
  controls.play.textContent = "Play";
});

document.addEventListener("keydown", (event) => {
  if (!enabled) return;
  const key = event.key.toLowerCase();
  if ([" ", "n", "p", "h", "i", "r", "escape"].includes(key)) {
    event.preventDefault();
  }
  if (key === " ") controls.play.click();
  if (key === "n") controls.next.click();
  if (key === "p") controls.prev.click();
  if (key === "h") controls.heading.click();
  if (key === "i") controls.image.click();
  if (key === "r" && currentIndex >= 0) narrate(currentIndex);
  if (key === "escape") {
    stopAudio();
    liveNarration.textContent = "Reading stopped.";
  }
});
