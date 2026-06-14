const demoScriptStatus = document.querySelector("#demoScriptStatus");
const demoScriptList = document.querySelector("#demoScriptList");
const demoApiCheckList = document.querySelector("#demoApiCheckList");
const awardEvidenceList = document.querySelector("#awardEvidenceList");
const submissionReadinessStatus = document.querySelector("#submissionReadinessStatus");
const submissionReadinessList = document.querySelector("#submissionReadinessList");
const copyEvidenceButton = document.querySelector("#copyEvidenceButton");
const evidenceCopyStatus = document.querySelector("#evidenceCopyStatus");
const budgetStatus = document.querySelector("#budgetStatus");
const modelBudgetList = document.querySelector("#modelBudgetList");
const runtimeStatusSummary = document.querySelector("#runtimeStatusSummary");
const runtimeStatusList = document.querySelector("#runtimeStatusList");
const runtimeSetupStatus = document.querySelector("#runtimeSetupStatus");
const runtimeSetupList = document.querySelector("#runtimeSetupList");
const imageReceiptStatus = document.querySelector("#imageReceiptStatus");
const imageReceiptList = document.querySelector("#imageReceiptList");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function roleLabel(role) {
  return role
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
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

async function copyTextToClipboard(text, successMessage, emptyMessage, unavailableMessage) {
  if (!text) {
    evidenceCopyStatus.textContent = emptyMessage;
    return false;
  }
  if (!navigator.clipboard) {
    evidenceCopyStatus.textContent = unavailableMessage;
    return false;
  }
  await navigator.clipboard.writeText(text);
  evidenceCopyStatus.textContent = successMessage;
  return true;
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
          <button class="demo-command-copy" type="button" data-command="${escapeHtml(item.curl)}">Copy curl</button>
          <code class="demo-api-command">${escapeHtml(item.powershell)}</code>
          <button class="demo-command-copy" type="button" data-command="${escapeHtml(item.powershell)}">Copy PowerShell</button>
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
          <p>${model.within_limit ? "Tiny Titan pass" : "Review parameter budget"}</p>
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

async function loadRuntimeStatus() {
  try {
    const payload = await postJson("/api/runtime-status");
    const brain = payload.reader_brain;
    const speech = payload.speech;
    const brainLabel = brain.available ? "llama.cpp online" : "llama.cpp fallback";
    const speechLabel = speech.available ? "Kokoro online" : "voice fallback";
    runtimeStatusSummary.textContent = `${brainLabel}, ${speechLabel}`;
    const runtimeItems = [
      ["Reader brain", payload.reader_brain],
      ["Vision", payload.vision],
      ["Speech", payload.speech],
      ["Image generation", payload.image_generation],
    ];
    runtimeStatusList.innerHTML = runtimeItems
      .map(([label, item]) => `
        <li>
          <div class="runtime-row">
            <span>${escapeHtml(label)}</span>
            <span class="runtime-pill">${escapeHtml(item.status)}</span>
          </div>
          <p>${escapeHtml(item.model)}${item.fallback ? ` | ${escapeHtml(item.fallback)}` : ""}</p>
        </li>
      `)
      .join("");
  } catch {
    runtimeStatusSummary.textContent = "Fallback ready";
    runtimeStatusList.innerHTML = `
      <li>
        <div class="runtime-row">
          <span>Runtime status</span>
          <span class="runtime-pill">offline</span>
        </div>
        <p>Live runtime status is unavailable; deterministic fallbacks remain documented.</p>
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
          <code class="runtime-command">${escapeHtml(step.command)}</code>
          <button class="runtime-command-copy" type="button" data-command="${escapeHtml(step.command)}">Copy command</button>
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

async function loadImageDescriptions() {
  try {
    const payload = await postJson("/api/image-descriptions");
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

copyEvidenceButton.addEventListener("click", async () => {
  try {
    const payload = await postJson("/api/evidence-bundle");
    const text = JSON.stringify(payload, null, 2);
    await copyTextToClipboard(
      text,
      "Evidence bundle copied.",
      "Evidence bundle is empty.",
      "Evidence bundle loaded, but clipboard access is unavailable.",
    );
  } catch (error) {
    evidenceCopyStatus.textContent = `Evidence bundle failed: ${error.message}`;
  }
});

demoApiCheckList.addEventListener("click", async (event) => {
  const button = event.target.closest(".demo-command-copy");
  if (!button) return;
  const command = button.dataset.command || "";
  await copyTextToClipboard(
    command,
    "Demo command copied.",
    "Demo command is empty.",
    "Command is visible, but clipboard access is unavailable.",
  );
});

runtimeSetupList.addEventListener("click", async (event) => {
  const button = event.target.closest(".runtime-command-copy");
  if (!button) return;
  const command = button.dataset.command || "";
  await copyTextToClipboard(
    command,
    "Runtime setup command copied.",
    "Runtime setup command is empty.",
    "Runtime setup command is visible, but clipboard access is unavailable.",
  );
});

loadDemoScript();
loadAwardEvidence();
loadSubmissionReadiness();
loadModelBudget();
loadRuntimeStatus();
loadRuntimeSetup();
loadImageDescriptions();
