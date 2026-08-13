import { extractCvText } from "../services/cvTextExtractor.js";
import {
  escapeHtml,
  formatDate,
  initials,
  renderLoading,
} from "../ui/sharedComponents.js";

export async function renderProfileView(container, { server, signal }) {
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">Profile</p>
        <h1>Your career profile</h1>
        <p class="page-subtitle">One saved CV gives every CareerCopilot workflow the context it needs.</p>
      </div>
    </section>
    ${renderLoading("Loading profile…")}
  `;

  const profile = await server.getProfile({ signal });
  if (signal.aborted) return;

  const hasCv = Boolean(profile.cv_text?.trim());
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">Profile</p>
        <h1>Your career profile</h1>
        <p class="page-subtitle">One saved CV gives every CareerCopilot workflow the context it needs.</p>
      </div>
      <span class="badge ${hasCv ? "badge--success" : "badge--neutral"}">
        ${hasCv ? "Ready for Copilot" : "CV needed"}
      </span>
    </section>

    <div class="profile-grid">
      <aside class="card profile-summary">
        <div class="profile-person">
          <div class="avatar avatar--large">${escapeHtml(initials(profile.name))}</div>
          <div>
            <h2>${escapeHtml(profile.name)}</h2>
            <a href="mailto:${escapeHtml(profile.email)}">${escapeHtml(profile.email)}</a>
          </div>
        </div>
        <dl class="profile-facts">
          <div>
            <dt>Profile ID</dt>
            <dd>${escapeHtml(profile.id)}</dd>
          </div>
          <div>
            <dt>Created</dt>
            <dd>${escapeHtml(formatDate(profile.created_at))}</dd>
          </div>
        </dl>
        <p class="muted-note">Profile details are read-only until the API supports editing them.</p>
      </aside>

      <section class="card cv-card" aria-labelledby="cv-title">
        <div class="card-heading-row">
          <div>
            <p class="eyebrow">CV</p>
            <h2 id="cv-title">Saved CV text</h2>
          </div>
          <span id="cv-state-badge" class="badge ${hasCv ? "badge--success" : "badge--neutral"}">
            ${hasCv ? "Text saved" : "No CV yet"}
          </span>
        </div>

        <label class="cv-dropzone" id="cv-dropzone" for="cv-file-input">
          <input
            id="cv-file-input"
            type="file"
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          />
          <span class="upload-icon" aria-hidden="true">↑</span>
          <strong>Drop your CV here or choose a file</strong>
          <span>PDF, DOCX, or TXT · up to 15 MB</span>
        </label>

        <div id="cv-upload-status" class="inline-message" aria-live="polite"></div>

        <div class="cv-preview-block">
          <div class="section-label-row">
            <span>Text preview</span>
            <span id="cv-character-count">${hasCv ? `${profile.cv_text.length.toLocaleString()} characters` : ""}</span>
          </div>
          <pre id="cv-preview" class="cv-preview ${hasCv ? "" : "cv-preview--empty"}">${
            hasCv
              ? escapeHtml(profile.cv_text)
              : "Upload a CV to extract and save its text. The original file never leaves your browser."
          }</pre>
        </div>
      </section>
    </div>
  `;

  const input = container.querySelector("#cv-file-input");
  const dropzone = container.querySelector("#cv-dropzone");
  const status = container.querySelector("#cv-upload-status");
  const preview = container.querySelector("#cv-preview");
  const characterCount = container.querySelector("#cv-character-count");
  const badge = container.querySelector("#cv-state-badge");

  async function processFile(file) {
    if (!file) return;

    input.disabled = true;
    dropzone.classList.add("is-busy");
    status.className = "inline-message inline-message--working";
    status.textContent = `Extracting text from ${file.name}…`;

    try {
      const cvText = await extractCvText(file);
      if (signal.aborted) return;

      preview.textContent = cvText;
      preview.classList.remove("cv-preview--empty");
      characterCount.textContent = `${cvText.length.toLocaleString()} characters`;
      status.textContent = "Text extracted. Saving it to your profile…";

      await server.uploadCv(cvText, { signal });
      if (signal.aborted) return;

      badge.className = "badge badge--success";
      badge.textContent = "Text saved";
      status.className = "inline-message inline-message--success";
      status.textContent = `${file.name} was processed. Only its extracted text was sent.`;
    } catch (error) {
      if (error.name === "AbortError") return;
      status.className = "inline-message inline-message--error";
      status.textContent = error.message;
    } finally {
      input.disabled = false;
      input.value = "";
      dropzone.classList.remove("is-busy");
    }
  }

  input.addEventListener("change", () => processFile(input.files?.[0]));

  for (const eventName of ["dragenter", "dragover"]) {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.remove("is-dragging");
    });
  }

  dropzone.addEventListener("drop", (event) => {
    processFile(event.dataTransfer?.files?.[0]);
  });
}
