import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/views.css";

import { careerCopilotServer } from "./api/CareerCopilotServer.js";
import { appState } from "./state/appState.js";
import { escapeHtml, renderError, renderLoading } from "./ui/sharedComponents.js";

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

function getTabFromLocation() {
  const tab = window.location.hash.replace(/^#\/?/, "");
  return VIEW_LOADERS[tab] ? tab : "profile";
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

        <nav class="tab-nav" aria-label="Primary navigation">
          ${TABS.map(
            (tab) => `
              <a href="#${tab.id}" data-tab="${tab.id}">
                ${escapeHtml(tab.label)}
              </a>
            `,
          ).join("")}
        </nav>
      </div>
    </header>

    <div id="connection-banner" class="connection-banner" aria-live="polite"></div>
    <main id="main-content" class="main-content" tabindex="-1">
      ${renderLoading("Connecting to CareerCopilot…")}
    </main>
  `;

  root.querySelector("#profile-selector").addEventListener("change", handleProfileChange);
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
start();
