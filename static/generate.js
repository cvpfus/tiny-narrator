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
        <h2>${escapeHtml(section.heading)}</h2>
        <p>${escapeHtml(section.body)}</p>
      </section>
    `)
    .join("");
  generatorStatus.textContent =
    `Generated with ${payload.model}; thumbnail from ${thumbnail.generation_model}; ${formatElapsed(payload.elapsed_ms)}.`;
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
