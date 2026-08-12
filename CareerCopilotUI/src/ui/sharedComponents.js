export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function formatDateTime(value, options = {}) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
    ...options,
  }).format(date);
}

export function formatDate(value) {
  return formatDateTime(value, { dateStyle: "medium", timeStyle: undefined });
}

export function formatTimeRange(startValue, endValue) {
  const start = new Date(startValue);
  const end = new Date(endValue);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return "Time unavailable";
  }

  const date = new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(start);
  const timeFormatter = new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });

  return `${date} · ${timeFormatter.format(start)}–${timeFormatter.format(end)}`;
}

export function initials(name) {
  const parts = String(name || "Career Copilot")
    .trim()
    .split(/\s+/)
    .filter(Boolean);

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function statusClass(status) {
  const normalized = String(status || "neutral")
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-");
  return `status-${normalized}`;
}

export function renderLoading(message = "Loading…") {
  return `
    <div class="state-panel" role="status" aria-live="polite">
      <span class="spinner" aria-hidden="true"></span>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

export function renderError(error, title = "Something went wrong") {
  return `
    <div class="state-panel state-panel--error" role="alert">
      <div class="state-icon" aria-hidden="true">!</div>
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(error?.message || error || "Unexpected error")}</p>
      </div>
    </div>
  `;
}

export function renderEmpty(title, message) {
  return `
    <div class="state-panel state-panel--empty">
      <div class="state-icon" aria-hidden="true">—</div>
      <div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
}
