import "fullcalendar/skeleton.css";
import "fullcalendar/themes/classic/theme.css";
import "fullcalendar/themes/classic/palette.css";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/views.css";

import { careerCopilotServer } from "./api/CareerCopilotServer.js";
import { appState } from "./state/appState.js";
import {
  escapeHtml,
  formatDateTime,
  renderError,
  renderLoading,
} from "./ui/sharedComponents.js";

const TABS = [
  { id: "profile", label: "Profile" },
  { id: "copilot", label: "CareerCopilot" },
  { id: "applications", label: "Applications" },
  { id: "emails", label: "Emails" },
  { id: "calendar", label: "Calendar" },
];

const VIEW_LOADERS = {
  profile: async () => (await import("./views/profileView.js")).renderProfileView,
  copilot: async () => (await import("./views/copilotView.js")).renderCopilotView,
  applications: async () =>
    (await import("./views/applicationsView.js")).renderApplicationsView,
  emails: async () => (await import("./views/emailsView.js")).renderEmailsView,
  calendar: async () => (await import("./views/calendarView.js")).renderCalendarView,
};

const root = document.querySelector("#app");
let activeController = null;
let activeCleanup = null;
let renderVersion = 0;
let notifications = [];
let notificationRequestNumber = 0;

function getTabFromLocation() {
  const tab = window.location.hash.replace(/^#\/?/, "");
  return VIEW_LOADERS[tab] ? tab : "copilot";
}

function renderShell() {
  root.innerHTML = `
    <a class="skip-link" href="#main-content">Skip to content</a>
    <header class="app-header">
      <div class="header-inner">
        <a class="brand" href="#profile" aria-label="CareerCopilot home">
          <span class="brand-mark" aria-hidden="true">C</span>
          <span>CareerCopilot</span>
        </a>

        <label class="profile-selector">
          <span>Active profile</span>
          <select id="profile-selector" disabled>
            <option>Loading profiles…</option>
          </select>
        </label>

        <div class="header-navigation">
          <nav class="tab-nav" aria-label="Primary navigation">
            ${TABS.map(
              (tab) => `
                <a href="#${tab.id}" data-tab="${tab.id}">
                  ${escapeHtml(tab.label)}
                </a>
              `,
            ).join("")}
          </nav>

          <div class="notification-center">
            <button
              id="notification-button"
              class="notification-button"
              type="button"
              aria-label="Notifications"
              aria-expanded="false"
              aria-controls="notification-dropdown"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M3.5 6.5h17v11h-17z"></path>
                <path d="m4 7 8 6 8-6"></path>
              </svg>
              <span id="notification-badge" class="notification-badge" hidden></span>
            </button>

            <section
              id="notification-dropdown"
              class="notification-dropdown"
              aria-label="Notifications"
              hidden
            >
              <header class="notification-dropdown-header">
                <div>
                  <p class="eyebrow">Updates</p>
                  <h2>Notifications</h2>
                </div>
                <button
                  id="mark-all-notifications-read"
                  class="notification-mark-all"
                  type="button"
                >
                  Mark all as read
                </button>
              </header>
              <div id="notification-list" class="notification-list" aria-live="polite">
                <div class="notification-empty">Loading notifications…</div>
              </div>
            </section>
          </div>
        </div>
      </div>
    </header>

    <div id="connection-banner" class="connection-banner" aria-live="polite"></div>
    <main id="main-content" class="main-content" tabindex="-1">
      ${renderLoading("Connecting to CareerCopilot…")}
    </main>
  `;

  root.querySelector("#profile-selector").addEventListener("change", handleProfileChange);
  root.querySelector("#notification-button").addEventListener("click", toggleNotifications);
  root
    .querySelector("#mark-all-notifications-read")
    .addEventListener("click", markAllNotificationsAsRead);
  root.querySelector("#notification-list").addEventListener("click", handleNotificationClick);
}

function renderNotifications() {
  const badge = root.querySelector("#notification-badge");
  const button = root.querySelector("#notification-button");
  const list = root.querySelector("#notification-list");
  const markAllButton = root.querySelector("#mark-all-notifications-read");
  if (!badge || !button || !list || !markAllButton) return;

  const unreadCount = notifications.filter((notification) => !notification.is_read).length;
  badge.hidden = unreadCount === 0;
  badge.textContent = unreadCount > 9 ? "9+" : String(unreadCount);
  button.setAttribute(
    "aria-label",
    unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications",
  );
  markAllButton.hidden = unreadCount === 0;

  if (notifications.length === 0) {
    list.innerHTML = `
      <div class="notification-empty">
        <span aria-hidden="true">✓</span>
        <strong>You're all caught up</strong>
        <p>CareerCopilot updates will appear here.</p>
      </div>
    `;
    return;
  }

  list.innerHTML = notifications
    .map(
      (notification) => `
        <button
          class="notification-item ${notification.is_read ? "" : "is-unread"}"
          type="button"
          data-notification-id="${escapeHtml(notification.id)}"
        >
          <span class="notification-unread-dot" aria-hidden="true"></span>
          <span class="notification-item-content">
            <strong>${escapeHtml(notification.title)}</strong>
            <span>${escapeHtml(notification.message)}</span>
            <time datetime="${escapeHtml(notification.created_at)}">
              ${escapeHtml(formatDateTime(notification.created_at))}
            </time>
          </span>
        </button>
      `,
    )
    .join("");
}

async function loadNotifications() {
  const currentRequest = ++notificationRequestNumber;
  try {
    const response = await careerCopilotServer.getNotifications();
    if (currentRequest !== notificationRequestNumber) return;
    notifications = Array.isArray(response) ? response : [];
    renderNotifications();
  } catch (error) {
    if (currentRequest !== notificationRequestNumber) return;
    const list = root.querySelector("#notification-list");
    if (list) {
      list.innerHTML = `
        <div class="notification-empty notification-empty--error">
          ${escapeHtml(error.message)}
        </div>
      `;
    }
  }
}

function closeNotifications() {
  const button = root.querySelector("#notification-button");
  const dropdown = root.querySelector("#notification-dropdown");
  if (!button || !dropdown) return;
  dropdown.hidden = true;
  button.setAttribute("aria-expanded", "false");
}

function toggleNotifications() {
  const button = root.querySelector("#notification-button");
  const dropdown = root.querySelector("#notification-dropdown");
  const shouldOpen = dropdown.hidden;
  dropdown.hidden = !shouldOpen;
  button.setAttribute("aria-expanded", String(shouldOpen));
  if (shouldOpen) loadNotifications();
}

async function handleNotificationClick(event) {
  const item = event.target.closest("[data-notification-id]");
  if (!item || !item.classList.contains("is-unread")) return;

  item.disabled = true;
  try {
    const updated = await careerCopilotServer.markNotificationAsRead(
      item.dataset.notificationId,
    );
    notifications = notifications.map((notification) =>
      notification.id === updated.id ? updated : notification,
    );
    renderNotifications();
  } catch (error) {
    item.disabled = false;
  }
}

async function markAllNotificationsAsRead() {
  const button = root.querySelector("#mark-all-notifications-read");
  button.disabled = true;
  try {
    await careerCopilotServer.markAllNotificationsAsRead();
    notifications = notifications.map((notification) => ({
      ...notification,
      is_read: true,
    }));
    renderNotifications();
  } finally {
    button.disabled = false;
  }
}

function updateActiveTab(tab) {
  appState.setActiveTab(tab);
  for (const link of root.querySelectorAll("[data-tab]")) {
    const isActive = link.dataset.tab === tab;
    link.classList.toggle("is-active", isActive);
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function updateProfileSelector() {
  const selector = root.querySelector("#profile-selector");
  selector.innerHTML = appState.profiles
    .map(
      (profile) => `
        <option value="${escapeHtml(profile.id)}" ${profile.id === appState.profileId ? "selected" : ""}>
          ${escapeHtml(profile.name)} · ${escapeHtml(profile.email)}
        </option>
      `,
    )
    .join("");
  selector.disabled = appState.profiles.length === 0;
}

async function loadProfiles() {
  const profiles = await careerCopilotServer.getProfiles();
  appState.setProfiles(profiles);
  appState.chooseAvailableProfile();
  careerCopilotServer.setProfileId(appState.profileId);
  updateProfileSelector();
}

function handleProfileChange(event) {
  appState.selectProfile(event.target.value);
  careerCopilotServer.setProfileId(appState.profileId);
  notifications = [];
  renderNotifications();
  loadNotifications();
  closeNotifications();
  renderActiveView();
}

async function renderActiveView() {
  const tab = getTabFromLocation();
  const container = root.querySelector("#main-content");
  const version = ++renderVersion;

  activeController?.abort();
  activeCleanup?.();
  activeCleanup = null;
  activeController = new AbortController();
  updateActiveTab(tab);
  document.title = `${TABS.find((candidate) => candidate.id === tab)?.label} · CareerCopilot`;

  if (!appState.profileId) {
    container.innerHTML = renderError(
      "No profile is available. Add a profile through the API, then retry.",
      "A profile is required",
    );
    return;
  }

  container.innerHTML = renderLoading(`Loading ${tab}…`);

  try {
    const renderView = await VIEW_LOADERS[tab]();
    if (version !== renderVersion) return;

    const cleanup = await renderView(container, {
      server: careerCopilotServer,
      signal: activeController.signal,
      refreshNotifications: loadNotifications,
    });

    if (version !== renderVersion) {
      cleanup?.();
      return;
    }

    activeCleanup = cleanup || null;
  } catch (error) {
    if (error.name === "AbortError" || version !== renderVersion) return;
    container.innerHTML = renderError(error, `Could not load ${tab}`);
  }
}

async function start() {
  renderShell();
  appState.setActiveTab(getTabFromLocation());
  updateActiveTab(appState.activeTab);

  try {
    await loadProfiles();
    await loadNotifications();
    root.querySelector("#connection-banner").innerHTML = "";
    await renderActiveView();
  } catch (error) {
    const banner = root.querySelector("#connection-banner");
    banner.innerHTML = `
      <div class="connection-banner__content" role="alert">
        <span>${escapeHtml(error.message)}</span>
        <button id="retry-connection" class="button button--small button--secondary" type="button">Retry</button>
      </div>
    `;
    root.querySelector("#main-content").innerHTML = renderError(
      error,
      "Could not connect to CareerCopilot",
    );
    banner.querySelector("#retry-connection").addEventListener("click", start);
  }
}

window.addEventListener("hashchange", renderActiveView);
document.addEventListener("click", (event) => {
  if (!event.target.closest(".notification-center")) {
    closeNotifications();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeNotifications();
});
start();
