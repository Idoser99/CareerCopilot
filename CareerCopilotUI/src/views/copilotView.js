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

export async function renderCopilotView(container, { server, signal }) {
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">CareerCopilot</p>
        <h1>Ask CareerCopilot to act</h1>
        <p class="page-subtitle">Use one prompt to search, tailor, submit, or review your job search.</p>
      </div>
      <span class="badge badge--success">Agent ready</span>
    </section>

    <section class="card copilot-card">
      <form id="copilot-form" class="prompt-form">
        <label for="copilot-prompt">What would you like to do?</label>
        <textarea
          id="copilot-prompt"
          rows="5"
          placeholder="For example: Find the best remote Python internship in Israel and tailor my CV."
          required
        ></textarea>
        <div class="prompt-actions">
          <span>Press <kbd>⌘</kbd>/<kbd>Ctrl</kbd> + <kbd>Enter</kbd> to run</span>
          <button class="button button--primary" id="run-agent-button" type="submit">
            Run CareerCopilot
          </button>
        </div>
      </form>

      <section class="agent-result" aria-labelledby="agent-result-title">
        <div class="card-heading-row">
          <div>
            <p class="eyebrow">Result</p>
            <h2 id="agent-result-title">CareerCopilot response</h2>
          </div>
        </div>
        <div id="agent-result-content" class="agent-result-content agent-result-content--empty" aria-live="polite">
          Your response will appear here.
        </div>
        <div id="execution-details-container"></div>
      </section>
    </section>
  `;

  const form = container.querySelector("#copilot-form");
  const prompt = container.querySelector("#copilot-prompt");
  const button = container.querySelector("#run-agent-button");
  const resultContent = container.querySelector("#agent-result-content");
  const detailsContainer = container.querySelector("#execution-details-container");

  async function submitPrompt() {
    const value = prompt.value.trim();
    if (!value || button.disabled) return;

    button.disabled = true;
    button.innerHTML = '<span class="button-spinner" aria-hidden="true"></span> Working…';
    resultContent.className = "agent-result-content agent-result-content--loading";
    resultContent.textContent = "CareerCopilot is working on your request…";
    detailsContainer.innerHTML = "";

    try {
      const result = await server.execute(value, { signal });
      if (signal.aborted) return;

      if (result.status !== "ok" || !result.response) {
        throw new Error(result.error || "CareerCopilot returned an empty response.");
      }

      resultContent.className = "agent-result-content markdown-content";
      renderMarkdown(resultContent, result.response);
      detailsContainer.innerHTML = renderSteps(result.steps);
    } catch (error) {
      if (error.name === "AbortError") return;
      resultContent.className = "agent-result-content agent-result-content--error";
      resultContent.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "Run CareerCopilot";
    }
  }

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
}
