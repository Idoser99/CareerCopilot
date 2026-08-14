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

function renderRows(applications) {
  return applications
    .map(
      (application) => `
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
        </tr>
      `,
    )
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
      <div id="applications-content">${renderLoading("Loading applications…")}</div>
    </section>
  `;

  const filter = container.querySelector("#application-status-filter");
  const content = container.querySelector("#applications-content");
  const count = container.querySelector("#application-count");
  let requestNumber = 0;

  async function loadApplications(status) {
    const currentRequest = ++requestNumber;
    content.innerHTML = renderLoading("Loading applications…");

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

  filter.addEventListener("change", () => loadApplications(filter.value));
  await loadApplications("all");
}
