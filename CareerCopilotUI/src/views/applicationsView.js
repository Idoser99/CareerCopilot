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
                    class="button button--secondary application-cv-download-button"
                    type="button"
                    data-download-application-cv="${escapeHtml(application.id)}"
                    aria-label="Download tailored CV for ${escapeHtml(application.job_title)}"
                  >Download</button>`
                : "—"
            }
          </td>
          <td>
            ${application.status === "pending" ? `
              <div class="application-decision-actions">
                <button
                  class="application-decision-button application-decision-button--accept"
                  type="button"
                  data-application-id="${escapeHtml(application.id)}"
                  data-decision="accepted"
                  aria-label="Simulate acceptance for ${escapeHtml(application.job_title)} at ${escapeHtml(application.company)}"
                >Accept</button>
                <button
                  class="application-decision-button application-decision-button--reject"
                  type="button"
                  data-application-id="${escapeHtml(application.id)}"
                  data-decision="rejected"
                  aria-label="Simulate rejection for ${escapeHtml(application.job_title)} at ${escapeHtml(application.company)}"
                >Reject</button>
              </div>
            ` : "—"}
          </td>
        </tr>
      `;
    })
    .join("");
}

export async function renderApplicationsView(
  container,
  { server, signal, refreshNotifications },
) {
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
      <div id="application-action-message" class="application-decision-message" aria-live="polite"></div>
      <div id="applications-content">${renderLoading("Loading applications…")}</div>
    </section>
  `;

  const filter = container.querySelector("#application-status-filter");
  const content = container.querySelector("#applications-content");
  const count = container.querySelector("#application-count");
  const actionMessage = container.querySelector("#application-action-message");
  let requestNumber = 0;

  function showActionMessage(message, type = "working") {
    actionMessage.className = `application-decision-message application-decision-message--${type}`;
    actionMessage.textContent = message;
  }

  async function loadApplications(status) {
    const currentRequest = ++requestNumber;
    content.innerHTML = renderLoading("Loading applications…");
    showActionMessage("");

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
                <th>Demo decision</th>
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

  async function handleDownload(event) {
    const button = event.target.closest?.("[data-download-application-cv]");
    if (!button) return;

    const applicationId = button.dataset.downloadApplicationCv;
    button.disabled = true;
    button.textContent = "Preparing…";
    showActionMessage("Preparing the tailored CV…");

    try {
      const { blob, filename } = await server.downloadApplicationCv(
        applicationId,
        { signal },
      );
      if (signal.aborted) return;

      triggerBrowserDownload(blob, filename);
      showActionMessage(`${filename} was downloaded.`, "success");
    } catch (error) {
      if (error.name === "AbortError") return;
      showActionMessage(error.message, "error");
    } finally {
      if (button.isConnected) {
        button.disabled = false;
        button.textContent = "Download";
      }
    }
  }

  async function handleDecision(event) {
    const button = event.target.closest("[data-decision]");
    if (!button) return;

    const { applicationId, decision } = button.dataset;
    const buttons = content.querySelectorAll("[data-decision]");
    buttons.forEach((candidate) => { candidate.disabled = true; });
    button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span>';
    showActionMessage(
      `Simulating ${decision} email and running CareerCopilot…`,
    );

    try {
      const response = await server.simulateApplicationDecision(
        applicationId,
        decision,
        { signal },
      );
      if (signal.aborted) return;

      await Promise.all([
        loadApplications(filter.value),
        refreshNotifications?.(),
      ]);
      showActionMessage(
        response.notification?.message || "The application update was processed.",
        "success",
      );
    } catch (error) {
      if (error.name === "AbortError") return;
      buttons.forEach((candidate) => { candidate.disabled = false; });
      button.textContent = decision === "accepted" ? "Accept" : "Reject";
      showActionMessage(error.message, "error");
    }
  }

  filter.addEventListener("change", () => loadApplications(filter.value));
  content.addEventListener("click", handleDownload);
  content.addEventListener("click", handleDecision);
  await loadApplications("all");
}
