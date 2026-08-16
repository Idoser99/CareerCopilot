import {
  escapeHtml,
  formatDateTime,
  renderEmpty,
  renderLoading,
  statusClass,
} from "../ui/sharedComponents.js";

const STATUSES = [
  "all",
  "draft",
  "pending",
  "accepted",
  "rejected",
  "withdrawn",
  "scheduled",
];

function triggerBrowserDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

function renderRows(applications) {
  return applications
    .map((application) => {
      const hasTailoredCv = Boolean(application.tailored_cv_text?.trim());
      return `
        <tr>
          <td>
            <div class="company-cell">
              <span class="company-mark">${escapeHtml(application.company?.[0] || "?")}</span>
              <strong>${escapeHtml(application.company)}</strong>
            </div>
          </td>
          <td>${escapeHtml(application.job_title)}</td>
          <td><span class="mono-text">${escapeHtml(application.job_id)}</span></td>
          <td>
            <span class="status-pill ${statusClass(application.status)}">
              ${escapeHtml(application.status)}
            </span>
          </td>
          <td>${escapeHtml(formatDateTime(application.submitted_at))}</td>
          <td>${escapeHtml(formatDateTime(application.created_at))}</td>
          <td>
            ${
              hasTailoredCv
                ? `<button
                    class="button button--small button--secondary"
                    type="button"
                    data-download-application-cv="${escapeHtml(application.id)}"
                    aria-label="Download tailored CV for ${escapeHtml(application.job_title)}"
                  >Download DOCX</button>`
                : "—"
            }
          </td>
        </tr>
      `;
    })
    .join("");
}

export async function renderApplicationsView(container, { server, signal }) {
  container.innerHTML = `
    <section class="page-heading page-heading--with-control">
      <div>
        <p class="eyebrow">Applications</p>
        <h1>Track every application</h1>
        <p class="page-subtitle">Drafts, pending decisions, and interviews stay together in one place.</p>
      </div>
      <label class="field field--compact">
        <span>Status</span>
        <select id="application-status-filter">
          ${STATUSES.map(
            (status) =>
              `<option value="${status}">${status === "all" ? "All statuses" : status[0].toUpperCase() + status.slice(1)}</option>`,
          ).join("")}
        </select>
      </label>
    </section>

    <section class="card applications-card">
      <div class="card-heading-row">
        <div>
          <p class="eyebrow">Overview</p>
          <h2>Applications</h2>
        </div>
        <span id="application-count" class="badge badge--info">—</span>
      </div>
      <div id="application-download-status" class="inline-message" aria-live="polite"></div>
      <div id="applications-content">${renderLoading("Loading applications…")}</div>
    </section>
  `;

  const filter = container.querySelector("#application-status-filter");
  const content = container.querySelector("#applications-content");
  const count = container.querySelector("#application-count");
  const downloadStatus = container.querySelector("#application-download-status");
  let requestNumber = 0;

  async function loadApplications(status) {
    const currentRequest = ++requestNumber;
    content.innerHTML = renderLoading("Loading applications…");
    downloadStatus.textContent = "";

    try {
      const response = await server.getApplications(status, { signal });
      if (signal.aborted || currentRequest !== requestNumber) return;

      const allApplications = Array.isArray(response) ? response : [];
      const applications =
        status && status !== "all"
          ? allApplications.filter((application) => application.status === status)
          : allApplications;

      count.textContent = `${applications.length} ${applications.length === 1 ? "application" : "applications"}`;

      if (applications.length === 0) {
        content.innerHTML = renderEmpty(
          "No matching applications",
          status === "all"
            ? "Applications created by CareerCopilot will appear here."
            : `There are no ${status} applications for this profile.`,
        );
        return;
      }

      content.innerHTML = `
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Role</th>
                <th>Job ID</th>
                <th>Status</th>
                <th>Submitted</th>
                <th>Created</th>
                <th>CV</th>
              </tr>
            </thead>
            <tbody>${renderRows(applications)}</tbody>
          </table>
        </div>
      `;
    } catch (error) {
      if (error.name === "AbortError") return;
      count.textContent = "Unavailable";
      content.innerHTML = `
        <div class="state-panel state-panel--error" role="alert">
          <div class="state-icon" aria-hidden="true">!</div>
          <div><h2>Could not load applications</h2><p>${escapeHtml(error.message)}</p></div>
        </div>
      `;
    }
  }

  content.addEventListener("click", async (event) => {
    const button = event.target.closest?.("[data-download-application-cv]");
    if (!button) return;

    const applicationId = button.dataset.downloadApplicationCv;
    button.disabled = true;
    button.textContent = "Preparing...";
    downloadStatus.className = "inline-message inline-message--working";
    downloadStatus.textContent = "Preparing the tailored CV...";

    try {
      const { blob, filename } = await server.downloadApplicationCv(
        applicationId,
        { signal },
      );
      if (signal.aborted) return;

      triggerBrowserDownload(blob, filename);
      downloadStatus.className = "inline-message inline-message--success";
      downloadStatus.textContent = `${filename} was downloaded.`;
    } catch (error) {
      if (error.name === "AbortError") return;
      downloadStatus.className = "inline-message inline-message--error";
      downloadStatus.textContent = error.message;
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = "Download DOCX";
      }
    }
  });

  filter.addEventListener("change", () => loadApplications(filter.value));
  await loadApplications("all");
}
