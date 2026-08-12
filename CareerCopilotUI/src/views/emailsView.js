import {
  escapeHtml,
  formatDateTime,
  initials,
  renderEmpty,
  renderLoading,
  statusClass,
} from "../ui/sharedComponents.js";

function sortEmails(emails) {
  return [...emails].sort(
    (first, second) => new Date(second.created_at) - new Date(first.created_at),
  );
}

function renderEmailList(emails, selectedId) {
  return emails
    .map(
      (email) => `
        <button
          class="email-list-item ${email.id === selectedId ? "is-selected" : ""}"
          type="button"
          data-email-id="${escapeHtml(email.id)}"
        >
          <span class="avatar avatar--small">${escapeHtml(initials(email.type))}</span>
          <span class="email-list-copy">
            <span class="email-list-meta">
              <strong>${escapeHtml(email.type)}</strong>
              <time>${escapeHtml(formatDateTime(email.created_at))}</time>
            </span>
            <span class="email-list-subject">${escapeHtml(email.subject)}</span>
            <span class="email-list-direction">${escapeHtml(email.direction)}</span>
          </span>
        </button>
      `,
    )
    .join("");
}

function renderEmailDetail(email) {
  return `
    <article class="email-detail">
      <div class="card-heading-row email-detail-heading">
        <div>
          <p class="eyebrow">Message</p>
          <h2>${escapeHtml(email.subject)}</h2>
        </div>
        <span class="status-pill ${statusClass(email.type)}">${escapeHtml(email.type)}</span>
      </div>

      <div class="email-detail-meta">
        <div class="avatar">${escapeHtml(initials(email.type))}</div>
        <div>
          <strong>${escapeHtml(email.direction === "inbound" ? "Incoming email" : "Outgoing email")}</strong>
          <span>Application ${escapeHtml(email.application_id)}</span>
        </div>
        <time>${escapeHtml(formatDateTime(email.created_at))}</time>
      </div>

      <div class="email-body">${escapeHtml(email.body)}</div>
    </article>
  `;
}

export async function renderEmailsView(container, { server, signal }) {
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">Emails</p>
        <h1>Employer responses, in one place</h1>
        <p class="page-subtitle">Review every application-related message associated with this profile.</p>
      </div>
    </section>
    ${renderLoading("Loading emails…")}
  `;

  const response = await server.getEmails({ signal });
  if (signal.aborted) return;

  const emails = sortEmails(Array.isArray(response) ? response : []);
  if (emails.length === 0) {
    container.innerHTML = `
      <section class="page-heading">
        <div>
          <p class="eyebrow">Emails</p>
          <h1>Employer responses, in one place</h1>
          <p class="page-subtitle">Review every application-related message associated with this profile.</p>
        </div>
      </section>
      <section class="card">${renderEmpty("No emails yet", "Application-related emails will appear here.")}</section>
    `;
    return;
  }

  let selectedId = emails[0].id;
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">Emails</p>
        <h1>Employer responses, in one place</h1>
        <p class="page-subtitle">Review every application-related message associated with this profile.</p>
      </div>
      <span class="badge badge--info">${emails.length} ${emails.length === 1 ? "message" : "messages"}</span>
    </section>

    <section class="email-layout">
      <aside class="card email-list-card" aria-label="Email list">
        <div class="card-heading-row">
          <h2>Inbox</h2>
        </div>
        <div id="email-list" class="email-list">
          ${renderEmailList(emails, selectedId)}
        </div>
      </aside>
      <section id="email-detail-card" class="card email-detail-card">
        ${renderEmailDetail(emails[0])}
      </section>
    </section>
  `;

  const list = container.querySelector("#email-list");
  const detail = container.querySelector("#email-detail-card");

  list.addEventListener("click", (event) => {
    const item = event.target.closest("[data-email-id]");
    if (!item) return;

    const email = emails.find((candidate) => candidate.id === item.dataset.emailId);
    if (!email) return;

    selectedId = email.id;
    list.innerHTML = renderEmailList(emails, selectedId);
    detail.innerHTML = renderEmailDetail(email);
  });
}
