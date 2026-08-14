import { escapeHtml } from "../ui/sharedComponents.js";
import { renderMarkdown } from "../ui/renderMarkdown.js";

function renderSteps(steps) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return "";
  }

  return `
    <details class="execution-details">
      <summary>Execution details <span>${steps.length}</span></summary>
      <ol>
        ${steps
          .map(
            (step) => `
              <li>
                <strong>${escapeHtml(step.module || "Agent step")}</strong>
              </li>
            `,
          )
          .join("")}
      </ol>
    </details>
  `;
}

function renderSessionList(sessions, activeSessionId) {
  if (sessions.length === 0) {
    return `
      <div class="session-list-empty">
        <span aria-hidden="true">✦</span>
        <p>Your conversations will appear here.</p>
      </div>
    `;
  }

  return sessions
    .map(
      (session) => `
        <button
          class="session-list-item ${session.id === activeSessionId ? "is-active" : ""}"
          type="button"
          data-session-id="${escapeHtml(session.id)}"
          aria-pressed="${session.id === activeSessionId}"
        >
          <span class="session-list-icon" aria-hidden="true">✦</span>
          <span>${escapeHtml(session.title || "New conversation")}</span>
        </button>
      `,
    )
    .join("");
}

function renderMessages(container, messages) {
  if (messages.length === 0) {
    container.innerHTML = `
      <div class="chat-empty">
        <span class="chat-empty-icon" aria-hidden="true">C</span>
        <h2>Start a new conversation</h2>
        <p>Ask CareerCopilot to find jobs, tailor your CV, review applications, or prepare for an interview.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = messages
    .map(
      (message, index) => `
        <article class="chat-message chat-message--${message.role}" data-message-index="${index}">
          <span class="chat-message-label">${message.role === "user" ? "You" : "CareerCopilot"}</span>
          <div class="chat-message-content ${message.role === "assistant" ? "markdown-content" : ""}"></div>
        </article>
      `,
    )
    .join("");

  messages.forEach((message, index) => {
    const content = container.querySelector(`[data-message-index="${index}"] .chat-message-content`);
    if (message.role === "assistant") {
      renderMarkdown(content, message.content);
    } else {
      content.textContent = message.content;
    }
  });

  container.scrollTop = container.scrollHeight;
}

function sessionStorageKey(profileId) {
  return `career-copilot-session:${profileId || "default"}`;
}

export async function renderCopilotView(container, { server, signal }) {
  let sessions = [];
  let activeSessionId = localStorage.getItem(sessionStorageKey(server.getProfileId()));
  let activeTitle = "New conversation";
  let messages = [];
  let latestSteps = [];
  let isBusy = false;

  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">CareerCopilot</p>
        <h1>Ask CareerCopilot to act</h1>
        <p class="page-subtitle">Continue a conversation or start a fresh job-search workflow.</p>
      </div>
      <span class="badge badge--success">Agent ready</span>
    </section>

    <section class="card copilot-workspace">
      <aside class="session-sidebar" aria-label="CareerCopilot conversations">
        <div class="session-sidebar-heading">
          <div>
            <p class="eyebrow">History</p>
            <h2>Conversations</h2>
          </div>
          <button
            class="button button--primary button--small new-session-button"
            id="new-session-button"
            type="button"
            aria-label="Start a new conversation"
          >
            <span aria-hidden="true">＋</span> New
          </button>
        </div>
        <div id="session-list" class="session-list" aria-live="polite"></div>
      </aside>

      <section class="conversation-panel" aria-labelledby="conversation-title">
        <header class="conversation-header">
          <div>
            <p class="eyebrow">Current conversation</p>
            <h2 id="conversation-title">New conversation</h2>
          </div>
          <span class="conversation-status"><i aria-hidden="true"></i> Ready</span>
        </header>

        <div id="chat-history" class="chat-history" aria-live="polite"></div>
        <div id="execution-details-container"></div>

        <form id="copilot-form" class="prompt-form chat-prompt-form">
          <label for="copilot-prompt">What would you like to do?</label>
          <textarea
            id="copilot-prompt"
            rows="3"
            placeholder="For example: Create a preparation plan for my next interview."
            required
          ></textarea>
          <div class="prompt-actions">
            <span>Press <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd> to run</span>
            <button class="button button--primary" id="run-agent-button" type="submit">
              Send to CareerCopilot
            </button>
          </div>
        </form>
      </section>
    </section>
  `;

  const form = container.querySelector("#copilot-form");
  const prompt = container.querySelector("#copilot-prompt");
  const button = container.querySelector("#run-agent-button");
  const newSessionButton = container.querySelector("#new-session-button");
  const sessionList = container.querySelector("#session-list");
  const conversationTitle = container.querySelector("#conversation-title");
  const conversationStatus = container.querySelector(".conversation-status");
  const chatHistory = container.querySelector("#chat-history");
  const detailsContainer = container.querySelector("#execution-details-container");

  function updateView() {
    sessionList.innerHTML = renderSessionList(sessions, activeSessionId);
    conversationTitle.textContent = activeTitle;
    renderMessages(chatHistory, messages);
    detailsContainer.innerHTML = renderSteps(latestSteps);
  }

  function rememberActiveSession() {
    const key = sessionStorageKey(server.getProfileId());
    if (activeSessionId) {
      localStorage.setItem(key, activeSessionId);
    } else {
      localStorage.removeItem(key);
    }
  }

  async function refreshSessions() {
    sessions = await server.getAgentSessions({ signal });
    if (activeSessionId && !sessions.some((session) => session.id === activeSessionId)) {
      activeSessionId = null;
    }
    updateView();
  }

  async function openSession(sessionId) {
    if (!sessionId || isBusy) return;

    isBusy = true;
    sessionList.classList.add("is-loading");
    detailsContainer.innerHTML = "";
    try {
      const session = await server.getAgentSession(sessionId, { signal });
      if (signal.aborted) return;

      activeSessionId = session.id;
      activeTitle = session.title || "New conversation";
      messages = Array.isArray(session.messages) ? session.messages : [];
      latestSteps = [];
      rememberActiveSession();
      updateView();
      prompt.focus();
    } finally {
      isBusy = false;
      sessionList.classList.remove("is-loading");
    }
  }

  async function createSession() {
    if (isBusy) return null;

    isBusy = true;
    newSessionButton.disabled = true;
    try {
      const session = await server.createAgentSession({ signal });
      if (signal.aborted) return null;

      activeSessionId = session.id;
      activeTitle = session.title || "New conversation";
      messages = [];
      latestSteps = [];
      sessions = [session, ...sessions.filter((item) => item.id !== session.id)];
      rememberActiveSession();
      updateView();
      prompt.focus();
      return session.id;
    } finally {
      isBusy = false;
      newSessionButton.disabled = false;
    }
  }

  async function submitPrompt() {
    const value = prompt.value.trim();
    if (!value || isBusy) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      sessionId = await createSession();
      if (!sessionId || signal.aborted) return;
    }

    isBusy = true;
    button.disabled = true;
    newSessionButton.disabled = true;
    button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Working…';
    conversationStatus.classList.add("is-working");
    conversationStatus.innerHTML = '<i aria-hidden="true"></i> Working';
    prompt.value = "";
    messages.push({ role: "user", content: value });
    latestSteps = [];
    updateView();

    try {
      const result = await server.execute(value, {
        sessionId,
        trackSession: true,
        signal,
      });
      if (signal.aborted) return;

      if (result.status !== "ok" || !result.response) {
        throw new Error(result.error || "CareerCopilot returned an empty response.");
      }

      activeSessionId = result.session_id || sessionId;
      messages.push({ role: "assistant", content: result.response });
      latestSteps = result.steps || [];
      rememberActiveSession();

      const storedSession = await server.getAgentSession(activeSessionId, { signal });
      if (signal.aborted) return;
      activeTitle = storedSession.title || activeTitle;
      messages = Array.isArray(storedSession.messages) ? storedSession.messages : messages;
      await refreshSessions();
      updateView();
    } catch (error) {
      if (error.name === "AbortError") return;
      messages.push({
        role: "assistant",
        content: `I could not complete that request. ${error.message}`,
      });
      updateView();
    } finally {
      isBusy = false;
      button.disabled = false;
      newSessionButton.disabled = false;
      button.textContent = "Send to CareerCopilot";
      conversationStatus.classList.remove("is-working");
      conversationStatus.innerHTML = '<i aria-hidden="true"></i> Ready';
      prompt.focus();
    }
  }

  sessionList.addEventListener("click", (event) => {
    const sessionButton = event.target.closest("[data-session-id]");
    if (sessionButton) {
      openSession(sessionButton.dataset.sessionId).catch((error) => {
        if (error.name !== "AbortError") {
          conversationStatus.textContent = error.message;
        }
      });
    }
  });

  newSessionButton.addEventListener("click", () => {
    createSession().catch((error) => {
      if (error.name !== "AbortError") {
        conversationStatus.textContent = error.message;
      }
    });
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitPrompt();
  });

  prompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      submitPrompt();
    }
  });

  sessions = await server.getAgentSessions({ signal });
  if (signal.aborted) return;

  const storedSessionExists = sessions.some((session) => session.id === activeSessionId);
  activeSessionId = storedSessionExists ? activeSessionId : sessions[0]?.id || null;
  rememberActiveSession();

  if (activeSessionId) {
    const session = await server.getAgentSession(activeSessionId, { signal });
    if (signal.aborted) return;
    activeTitle = session.title || "New conversation";
    messages = Array.isArray(session.messages) ? session.messages : [];
  }

  updateView();
}
