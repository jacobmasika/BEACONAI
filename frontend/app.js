import { pipeline } from "https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2";

const API_BASE = (() => {
  const { protocol, hostname, port, origin } = window.location;
  const isLocalStaticPreview =
    (hostname === "localhost" || hostname === "127.0.0.1") && (port === "8080" || port === "5500");

  if (isLocalStaticPreview) {
    return `${protocol}//${hostname}:5000/api`;
  }

  return `${origin}/api`;
})();
const DB_NAME = "beaconai-local";
const STORE_NAME = "pending-sightings";
const VECTOR_DIMENSIONS = 512;
const MODEL_LOAD_TIMEOUT_MS = 15000;
const MODEL_INFERENCE_TIMEOUT_MS = 12000;
const STORED_PHOTO_MAX_EDGE = 768;
const STORED_PHOTO_QUALITY = 0.78;

const state = {
  embedder: null,
  currentEmbedding: null,
  publicCasePreviewUrl: null,
};

const networkStatusEl = document.getElementById("networkStatus");
const modelStatusEl = document.getElementById("modelStatus");
const embeddingMetaEl = document.getElementById("embeddingMeta");
const matchListEl = document.getElementById("matchList");
const publicCaseMetaEl = document.getElementById("publicCaseMeta");
const publicCaseListEl = document.getElementById("publicCaseList");
const aiSearchMetaEl = document.getElementById("aiSearchMeta");
const aiSearchResultsEl = document.getElementById("aiSearchResults");

const aiSearchForm = document.getElementById("aiSearchForm");
const aiSearchTextInput = document.getElementById("aiSearchTextInput");
const aiSearchPhotoInput = document.getElementById("aiSearchPhotoInput");
const clearAiSearchPhotoButton = document.getElementById("clearAiSearchPhotoButton");

const sightingForm = document.getElementById("sightingForm");
const imageInput = document.getElementById("imageInput");
const clearSightingPhotoButton = document.getElementById("clearSightingPhotoButton");
const descriptionInput = document.getElementById("descriptionInput");
const deviceIdInput = document.getElementById("deviceIdInput");
const embedButton = document.getElementById("embedButton");
const submitButton = document.getElementById("submitButton");
const refreshMatchesButton = document.getElementById("refreshMatchesButton");
const refreshPublicCasesButton = document.getElementById("refreshPublicCasesButton");

const publicCaseForm = document.getElementById("publicCaseForm");
const reporterNameInput = document.getElementById("reporterNameInput");
const reporterRelationshipInput = document.getElementById("reporterRelationshipInput");
const reporterContactInput = document.getElementById("reporterContactInput");
const missingPersonNameInput = document.getElementById("missingPersonNameInput");
const missingPersonPhotoInput = document.getElementById("missingPersonPhotoInput");
const missingPersonPhotoPreview = document.getElementById("missingPersonPhotoPreview");
const missingPersonPhotoPreviewWrap = document.getElementById("missingPersonPhotoPreviewWrap");
const clearMissingPersonPhotoButton = document.getElementById("clearMissingPersonPhotoButton");
const removePreviewPhotoButton = document.getElementById("removePreviewPhotoButton");
const missingPersonAgeInput = document.getElementById("missingPersonAgeInput");
const missingSinceInput = document.getElementById("missingSinceInput");
const lastSeenLocationInput = document.getElementById("lastSeenLocationInput");
const circumstancesInput = document.getElementById("circumstancesInput");

function updateNetworkStatus() {
  networkStatusEl.textContent = navigator.onLine ? "Online" : "Offline";
  networkStatusEl.className = `pill ${navigator.onLine ? "" : "warning"}`.trim();
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read selected photo"));
    reader.readAsDataURL(file);
  });
}

function withTimeout(promise, timeoutMs, message) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs);
    promise
      .then((value) => {
        clearTimeout(timer);
        resolve(value);
      })
      .catch((error) => {
        clearTimeout(timer);
        reject(error);
      });
  });
}

function normalizeVector(values) {
  const magnitude = Math.sqrt(values.reduce((sum, value) => sum + value * value, 0));
  if (!magnitude) {
    return values;
  }
  return values.map((value) => value / magnitude);
}

async function buildFallbackEmbeddingFromFile(file) {
  if (!window.crypto?.subtle) {
    throw new Error("Fallback embedding unavailable in this browser");
  }

  const bytes = new Uint8Array(await file.arrayBuffer());
  const digest = new Uint8Array(await window.crypto.subtle.digest("SHA-256", bytes));
  const vector = Array.from({ length: VECTOR_DIMENSIONS }, (_, index) => (digest[index % digest.length] / 127.5) - 1);
  return normalizeVector(vector);
}

async function createEmbeddingFromFile(file, { allowFallback = true } = {}) {
  try {
    const model = await withTimeout(getEmbedder(), MODEL_LOAD_TIMEOUT_MS, "Photo tool timed out while loading");
    const imageUrl = URL.createObjectURL(file);
    try {
      const output = await withTimeout(
        model(imageUrl, { pooling: "mean", normalize: true }),
        MODEL_INFERENCE_TIMEOUT_MS,
        "Photo tool timed out while processing the image"
      );
      return { embedding: normalizeEmbedding(output), method: "model" };
    } finally {
      URL.revokeObjectURL(imageUrl);
    }
  } catch (error) {
    if (!allowFallback) {
      throw error;
    }

    const embedding = await buildFallbackEmbeddingFromFile(file);
    modelStatusEl.textContent = "Photo tool slow. Using fallback embedding.";
    modelStatusEl.className = "pill warning";
    return { embedding, method: "fallback" };
  }
}

async function resizeImageForStorage(file, maxEdge = STORED_PHOTO_MAX_EDGE, quality = STORED_PHOTO_QUALITY) {
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("Could not decode selected photo"));
      img.src = objectUrl;
    });

    const width = image.naturalWidth || image.width;
    const height = image.naturalHeight || image.height;
    const scale = Math.min(1, maxEdge / Math.max(width, height));
    const targetWidth = Math.max(1, Math.round(width * scale));
    const targetHeight = Math.max(1, Math.round(height * scale));

    const canvas = document.createElement("canvas");
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      throw new Error("Could not initialize photo canvas");
    }

    ctx.drawImage(image, 0, 0, targetWidth, targetHeight);
    return canvas.toDataURL("image/jpeg", quality);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function resetSightingFormState() {
  state.currentEmbedding = null;
  imageInput.value = "";
  descriptionInput.value = "";
  submitButton.disabled = true;
  if (clearSightingPhotoButton) {
    clearSightingPhotoButton.hidden = true;
  }
}

function clearPublicCasePreview() {
  if (state.publicCasePreviewUrl) {
    URL.revokeObjectURL(state.publicCasePreviewUrl);
    state.publicCasePreviewUrl = null;
  }
  if (missingPersonPhotoPreviewWrap) {
    missingPersonPhotoPreviewWrap.hidden = true;
  }
  missingPersonPhotoPreview.removeAttribute("src");
  missingPersonPhotoInput.value = "";
  if (clearMissingPersonPhotoButton) {
    clearMissingPersonPhotoButton.hidden = true;
  }
}

function clearAiSearchPhotoSelection() {
  aiSearchPhotoInput.value = "";
  if (clearAiSearchPhotoButton) {
    clearAiSearchPhotoButton.hidden = true;
  }
}

function clearSightingPhotoSelection() {
  imageInput.value = "";
  state.currentEmbedding = null;
  submitButton.disabled = true;
  embeddingMetaEl.textContent = "Photo removed. Please upload a new photo.";
  if (clearSightingPhotoButton) {
    clearSightingPhotoButton.hidden = true;
  }
}

function normalizeEmbedding(rawOutput) {
  const flat = Array.isArray(rawOutput?.data)
    ? rawOutput.data
    : Array.from(rawOutput?.data || []);

  if (!flat.length) {
    throw new Error("Model output did not contain vector data");
  }

  // Keep vector length stable for backend validation and ANN indexing.
  if (flat.length >= VECTOR_DIMENSIONS) {
    return flat.slice(0, VECTOR_DIMENSIONS).map(Number);
  }

  const padded = [...flat];
  while (padded.length < VECTOR_DIMENSIONS) {
    padded.push(0);
  }
  return padded.map(Number);
}

function getConfidenceMeta(similarity) {
  if (similarity === null || similarity === undefined) {
    return { label: "Text Only", className: "confidence-keyword" };
  }

  const value = Number(similarity);
  if (value >= 0.85) {
    return { label: "Strong Match", className: "confidence-high" };
  }
  if (value >= 0.7) {
    return { label: "Possible Match", className: "confidence-medium" };
  }
  return { label: "Weak Match", className: "confidence-low" };
}

async function getEmbedder() {
  if (!state.embedder) {
    modelStatusEl.textContent = "Preparing photo tool...";
    modelStatusEl.className = "pill warning";
    state.embedder = await pipeline("image-feature-extraction", "Xenova/clip-vit-base-patch32");
    modelStatusEl.textContent = "Ready";
    modelStatusEl.className = "pill";
  }
  return state.embedder;
}

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);

    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE_NAME, { keyPath: "id", autoIncrement: true });
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function savePending(payload) {
  const db = await openDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).add(payload);
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function getPending() {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const req = tx.objectStore(STORE_NAME).getAll();
    req.onsuccess = () => resolve(req.result || []);
    req.onerror = () => reject(req.error);
  });
}

async function clearPending() {
  const db = await openDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    tx.objectStore(STORE_NAME).clear();
    tx.oncomplete = resolve;
    tx.onerror = () => reject(tx.error);
  });
}

async function postSighting(payload) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);

  try {
    const response = await fetch(`${API_BASE}/sighting`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const responseText = await response.text();
    let result;
    try {
      result = responseText ? JSON.parse(responseText) : {};
    } catch {
      result = { error: responseText || "Unexpected API response" };
    }

    if (!response.ok) {
      throw new Error(result.error || `Sighting submission failed (${response.status})`);
    }

    return result;
  } finally {
    clearTimeout(timeout);
  }
}

async function syncPendingSightings() {
  if (!navigator.onLine) {
    return;
  }

  const pending = await getPending();
  if (!pending.length) {
    return;
  }

  for (const payload of pending) {
    try {
      await postSighting(payload);
    } catch (error) {
      console.warn("Sync interrupted due to connectivity instability", error);
      return;
    }
  }

  await clearPending();
}

async function renderMatches() {
  matchListEl.textContent = "Loading possible matches...";

  try {
    const response = await fetch(`${API_BASE}/matches?limit=10`);
    const responseText = await response.text();
    let data;
    try {
      data = responseText ? JSON.parse(responseText) : {};
    } catch {
      data = { error: responseText || "Unexpected API response" };
    }

    if (!response.ok) {
      throw new Error(data.error || `Could not load matches (${response.status})`);
    }

    if (!data.matches || !data.matches.length) {
      matchListEl.textContent = "No possible matches yet.";
      return;
    }

    matchListEl.innerHTML = "";
    data.matches.forEach((item) => {
      const row = document.createElement("article");
      row.className = "list-item";
      row.innerHTML = `
        <div><strong>Sighting Report ID:</strong> ${item.report_id}</div>
        <div><strong>Match Strength:</strong> ${(item.similarity_score || 0).toFixed(4)}</div>
        <div><strong>Details:</strong> ${item.sighting_text}</div>
      `;
      matchListEl.appendChild(row);
    });
  } catch (error) {
    matchListEl.textContent = error.message || "Could not load possible matches.";
  }
}

async function postPublicCase(payload) {
  let response;
  try {
    response = await fetch(`${API_BASE}/public/cases`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("We could not reach the server. Please make sure it is running.");
  }

  const responseText = await response.text();
  let result;
  try {
    result = responseText ? JSON.parse(responseText) : {};
  } catch {
    result = { error: responseText || "Unexpected API response" };
  }

  if (!response.ok) {
    throw new Error(result.error || `Failed to submit case (${response.status})`);
  }

  return result;
}

async function postMissingSearch(payload) {
  let response;
  try {
    response = await fetch(`${API_BASE}/search/missing`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("We could not reach the server. Please make sure it is running.");
  }

  const responseText = await response.text();
  let result;
  try {
    result = responseText ? JSON.parse(responseText) : {};
  } catch {
    result = { error: responseText || "Unexpected API response" };
  }

  if (!response.ok) {
    throw new Error(result.error || `Search failed (${response.status})`);
  }

  return result;
}

async function postPublicCaseEmbeddingReindex(reportId, embedding) {
  let response;
  try {
    response = await fetch(`${API_BASE}/public/cases/reindex-embedding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        report_id: reportId,
        embedding,
      }),
    });
  } catch {
    throw new Error("We could not reach the server. Please make sure it is running.");
  }

  const responseText = await response.text();
  let result;
  try {
    result = responseText ? JSON.parse(responseText) : {};
  } catch {
    result = { error: responseText || "Unexpected API response" };
  }

  if (!response.ok) {
    throw new Error(result.error || `Embedding reindex failed (${response.status})`);
  }

  return result;
}

async function ensurePublicCasePhotoEmbeddings() {
  const response = await fetch(`${API_BASE}/public/cases?limit=200`);
  const responseText = await response.text();
  let data;
  try {
    data = responseText ? JSON.parse(responseText) : {};
  } catch {
    data = { error: responseText || "Unexpected API response" };
  }

  if (!response.ok) {
    throw new Error(data.error || `Could not load case reports (${response.status})`);
  }

  const cases = Array.isArray(data.cases) ? data.cases : [];

  const pending = cases.filter(
    (item) => item.missing_person_photo_data_url && !item.has_photo_embedding && item.report_id
  );

  if (!pending.length) {
    return 0;
  }

  const model = await getEmbedder();
  let updated = 0;

  for (const item of pending) {
    try {
      const output = await withTimeout(
        model(item.missing_person_photo_data_url, { pooling: "mean", normalize: true }),
        MODEL_INFERENCE_TIMEOUT_MS,
        "Backfill embedding timeout"
      );
      const embedding = normalizeEmbedding(output);
      await postPublicCaseEmbeddingReindex(item.report_id, embedding);
      updated += 1;
    } catch (error) {
      console.warn("Could not backfill photo embedding for report", item.report_id, error);
    }
  }

  return updated;
}

async function renderPublicCases() {
  publicCaseListEl.textContent = "Loading case reports...";

  try {
    const response = await fetch(`${API_BASE}/public/cases?limit=10`);
    const responseText = await response.text();
    let data;
    try {
      data = responseText ? JSON.parse(responseText) : {};
    } catch {
      data = { error: responseText || "Unexpected API response" };
    }

    if (!response.ok) {
      throw new Error(data.error || `Could not load case reports (${response.status})`);
    }

    if (!data.cases || !data.cases.length) {
      publicCaseListEl.textContent = "No case reports yet.";
      return;
    }

    publicCaseListEl.innerHTML = "";
    data.cases.forEach((item) => {
      const row = document.createElement("article");
      row.className = "list-item";
      const imageBlock = item.missing_person_photo_data_url
        ? `<img class="case-photo" src="${item.missing_person_photo_data_url}" alt="${item.missing_person_name} photo" />`
        : "";
      row.innerHTML = `
        <div><strong>Missing Person:</strong> ${item.missing_person_name}</div>
        <div><strong>Reported by:</strong> ${item.reporter_name} (${item.reporter_relationship})</div>
        <div><strong>Contact:</strong> ${item.reporter_contact}</div>
        <div><strong>Last Seen:</strong> ${item.last_seen_location}</div>
        <div><strong>Missing Since:</strong> ${item.missing_since_iso || "Not specified"}</div>
        <div><strong>Details:</strong> ${item.circumstances}</div>
        ${imageBlock}
      `;
      publicCaseListEl.appendChild(row);
    });
  } catch (error) {
    publicCaseListEl.textContent = error.message || "Could not load case reports.";
  }
}

embedButton.addEventListener("click", async () => {
  if (!imageInput.files?.length) {
    embeddingMetaEl.textContent = "Please upload a photo first.";
    return;
  }

  try {
    const imageFile = imageInput.files[0];
    const { embedding, method } = await createEmbeddingFromFile(imageFile, { allowFallback: true });
    state.currentEmbedding = embedding;

    embeddingMetaEl.textContent =
      method === "fallback"
        ? "Photo ready with fallback embedding. You can still send now."
        : "Photo is ready to send.";
    submitButton.disabled = false;
  } catch (error) {
    console.error(error);
    embeddingMetaEl.textContent = "Could not prepare this photo.";
  }
});

sightingForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!state.currentEmbedding) {
    embeddingMetaEl.textContent = "Please click Prepare Photo first.";
    return;
  }

  const payload = {
    source_device_id: deviceIdInput.value.trim() || "unknown-device",
    description: descriptionInput.value.trim(),
    captured_at_iso: new Date().toISOString(),
    location: {},
    embedding: state.currentEmbedding,
  };

  if (!payload.description) {
    embeddingMetaEl.textContent = "Please add details before sending.";
    return;
  }

  try {
    if (!navigator.onLine) {
      await savePending(payload);
      embeddingMetaEl.textContent = "You are offline. We saved this report and will send it when connection returns.";
      resetSightingFormState();
      return;
    }

    const result = await postSighting(payload);
    embeddingMetaEl.textContent = `Report sent. Status: ${result.status || "received"}`;
    resetSightingFormState();
    await renderMatches();
  } catch (error) {
    await savePending(payload);
    embeddingMetaEl.textContent = "Connection was unstable. We saved this report and will try again automatically.";
    resetSightingFormState();
  }
});

publicCaseForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const ageValue = missingPersonAgeInput.value.trim();
  let photoDataUrl = null;
  let photoEmbedding = null;
  const selectedPhoto = missingPersonPhotoInput.files?.[0];
  if (selectedPhoto) {
    try {
      photoDataUrl = await resizeImageForStorage(selectedPhoto);
    } catch (error) {
      publicCaseMetaEl.textContent = "Could not read the selected photo.";
      return;
    }

    try {
      const { embedding, method } = await createEmbeddingFromFile(selectedPhoto, { allowFallback: true });
      photoEmbedding = embedding;
      if (method === "fallback") {
        publicCaseMetaEl.textContent = "Photo attached. Using fallback embedding due model delay.";
      }
    } catch {
      // Do not block report submission when model inference is unavailable.
      photoEmbedding = null;
      publicCaseMetaEl.textContent = "Photo attached. AI embedding unavailable, but report can still be submitted.";
    }
  }

  const payload = {
    reporter_name: reporterNameInput.value.trim(),
    reporter_relationship: reporterRelationshipInput.value.trim(),
    reporter_contact: reporterContactInput.value.trim(),
    missing_person_name: missingPersonNameInput.value.trim(),
    missing_person_photo_embedding: photoEmbedding,
    missing_person_age: ageValue ? Number(ageValue) : null,
    missing_since_iso: missingSinceInput.value ? new Date(missingSinceInput.value).toISOString() : null,
    last_seen_location: lastSeenLocationInput.value.trim(),
    circumstances: circumstancesInput.value.trim(),
  };

  if (
    !payload.reporter_name ||
    !payload.reporter_relationship ||
    !payload.reporter_contact ||
    !payload.missing_person_name ||
    !payload.last_seen_location ||
    !payload.circumstances
  ) {
    publicCaseMetaEl.textContent = "Please complete all required fields.";
    return;
  }

  try {
    const result = await postPublicCase(payload);
    publicCaseMetaEl.textContent = `Case report submitted. Reference ID: ${result.report_id}`;
    publicCaseForm.reset();
    clearPublicCasePreview();
    await renderPublicCases();
  } catch (error) {
    publicCaseMetaEl.textContent = error.message || "Could not submit case report.";
  }
});

missingPersonPhotoInput.addEventListener("change", () => {
  if (state.publicCasePreviewUrl) {
    URL.revokeObjectURL(state.publicCasePreviewUrl);
    state.publicCasePreviewUrl = null;
  }

  const selectedPhoto = missingPersonPhotoInput.files?.[0];
  if (!selectedPhoto) {
    if (missingPersonPhotoPreviewWrap) {
      missingPersonPhotoPreviewWrap.hidden = true;
    }
    missingPersonPhotoPreview.removeAttribute("src");
    if (clearMissingPersonPhotoButton) {
      clearMissingPersonPhotoButton.hidden = true;
    }
    return;
  }

  try {
    // Use object URL instead of base64 conversion for instant preview without data overhead
    const photoUrl = URL.createObjectURL(selectedPhoto);
    state.publicCasePreviewUrl = photoUrl;
    missingPersonPhotoPreview.src = photoUrl;
    if (missingPersonPhotoPreviewWrap) {
      missingPersonPhotoPreviewWrap.hidden = false;
    }
    if (clearMissingPersonPhotoButton) {
      clearMissingPersonPhotoButton.hidden = false;
    }
  } catch {
    if (missingPersonPhotoPreviewWrap) {
      missingPersonPhotoPreviewWrap.hidden = true;
    }
    missingPersonPhotoPreview.removeAttribute("src");
    publicCaseMetaEl.textContent = "Could not preview the selected photo.";
  }
});

if (clearMissingPersonPhotoButton) {
  clearMissingPersonPhotoButton.addEventListener("click", clearPublicCasePreview);
}

if (removePreviewPhotoButton) {
  removePreviewPhotoButton.addEventListener("click", clearPublicCasePreview);
}

if (clearSightingPhotoButton) {
  clearSightingPhotoButton.addEventListener("click", clearSightingPhotoSelection);
}

imageInput.addEventListener("change", () => {
  if (clearSightingPhotoButton) {
    clearSightingPhotoButton.hidden = !imageInput.files?.length;
  }
});

if (clearAiSearchPhotoButton) {
  clearAiSearchPhotoButton.addEventListener("click", clearAiSearchPhotoSelection);
}

aiSearchPhotoInput.addEventListener("change", () => {
  if (clearAiSearchPhotoButton) {
    clearAiSearchPhotoButton.hidden = !aiSearchPhotoInput.files?.length;
  }
});

aiSearchForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const searchText = aiSearchTextInput.value.trim();
  const searchPhoto = aiSearchPhotoInput.files?.[0];

  if (!searchText && !searchPhoto) {
    aiSearchMetaEl.textContent = "Please type details or upload a photo.";
    return;
  }

  let embedding = null;

  try {
    if (searchPhoto) {
      const { embedding: preparedEmbedding, method } = await createEmbeddingFromFile(searchPhoto, { allowFallback: true });
      embedding = preparedEmbedding;
      if (method === "fallback") {
        aiSearchMetaEl.textContent = "Running AI search with fallback embedding...";
      }
    }
  } catch (error) {
    aiSearchMetaEl.textContent = "Could not prepare your search photo.";
    return;
  }

  try {
    aiSearchMetaEl.textContent = "Running AI search...";
    const result = await postMissingSearch({
      description: searchText,
      embedding,
      image_search: Boolean(searchPhoto),
      limit: 10,
    });

    if (!result.results || !result.results.length) {
      aiSearchResultsEl.textContent = "No possible matches found.";
      aiSearchMetaEl.textContent = "Search complete.";
      return;
    }

    aiSearchResultsEl.innerHTML = "";
    result.results.forEach((item) => {
      const sourceLabel = item.source === "public_case_report" ? "Reported Cases" : "Official Missing Persons List";
      const caseId = item.government_case_id || item.id || "N/A";
      const imageBlock = item.missing_person_photo_data_url
        ? `<img class="case-photo" src="${item.missing_person_photo_data_url}" alt="${item.full_name}" />`
        : "";
      const confidence = getConfidenceMeta(item.similarity);
      const similarityLabel =
        item.similarity !== null && item.similarity !== undefined
          ? Number(item.similarity).toFixed(4)
          : "Text match";
      const row = document.createElement("article");
      row.className = "list-item";
      if (item.source === "public_case_report") {
        row.innerHTML = `
          <div><strong>Data Source:</strong> ${sourceLabel}</div>
          <div><strong>Match Confidence:</strong> <span class="confidence-badge ${confidence.className}">${confidence.label}</span></div>
          <div><strong>Report ID:</strong> ${item.report_id || item.id || "N/A"}</div>
          <div><strong>Person Name:</strong> ${item.missing_person_name || item.full_name || "N/A"}</div>
          <div><strong>Age:</strong> ${item.missing_person_age ?? "Not specified"}</div>
          <div><strong>Missing Since:</strong> ${item.missing_since_iso || "Not specified"}</div>
          <div><strong>Last Seen:</strong> ${item.last_seen_location || "Not specified"}</div>
          <div><strong>Details:</strong> ${item.circumstances || item.description || "N/A"}</div>
          <div><strong>Reporter:</strong> ${item.reporter_name || "N/A"} (${item.reporter_relationship || "N/A"})</div>
          <div><strong>Reporter Contact:</strong> ${item.reporter_contact || "N/A"}</div>
          <div><strong>Status:</strong> ${item.status || "submitted"}</div>
          <div><strong>Reported On:</strong> ${item.created_at || "N/A"}</div>
          <div><strong>Match Strength:</strong> ${similarityLabel}</div>
          ${imageBlock}
        `;
      } else {
        row.innerHTML = `
          <div><strong>Data Source:</strong> ${sourceLabel}</div>
          <div><strong>Match Confidence:</strong> <span class="confidence-badge ${confidence.className}">${confidence.label}</span></div>
          <div><strong>Person Name:</strong> ${item.full_name}</div>
          <div><strong>Details:</strong> ${item.description}</div>
          <div><strong>Official Case ID:</strong> ${caseId}</div>
          <div><strong>Match Strength:</strong> ${similarityLabel}</div>
          ${imageBlock}
        `;
      }
      aiSearchResultsEl.appendChild(row);
    });
    aiSearchMetaEl.textContent = `Search complete. ${result.count} result(s).`;
  } catch (error) {
    aiSearchResultsEl.textContent = "";
    aiSearchMetaEl.textContent = error.message || "Search failed.";
  }
});

refreshMatchesButton.addEventListener("click", renderMatches);
refreshPublicCasesButton.addEventListener("click", renderPublicCases);
window.addEventListener("online", syncPendingSightings);
window.addEventListener("online", updateNetworkStatus);
window.addEventListener("offline", updateNetworkStatus);

updateNetworkStatus();
renderMatches();
renderPublicCases();
syncPendingSightings();

