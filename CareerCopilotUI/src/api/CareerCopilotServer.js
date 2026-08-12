export class CareerCopilotApiError extends Error {
  constructor(message, { status = 0, details = null } = {}) {
    super(message);
    this.name = "CareerCopilotApiError";
    this.status = status;
    this.details = details;
  }
}

export class CareerCopilotServer {
  constructor({ baseUrl = "/api", fetchImpl = globalThis.fetch } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.fetchImpl = fetchImpl.bind(globalThis);
    this.profileId = null;
  }

  setProfileId(profileId) {
    this.profileId = profileId || null;
  }

  getProfileId() {
    return this.profileId;
  }

  getProfiles({ signal } = {}) {
    return this.#request("/profiles", { signal });
  }

  getProfile({ signal } = {}) {
    return this.#request("/profile", { signal });
  }

  uploadCv(cvText, { signal } = {}) {
    return this.#request("/profile/cv", {
      method: "POST",
      body: { cv_text: cvText },
      signal,
    });
  }

  execute(prompt, { signal } = {}) {
    return this.#request("/execute", {
      method: "POST",
      body: { prompt },
      signal,
    });
  }

  getApplications(status = null, { signal } = {}) {
    return this.#request("/applications", {
      query: status && status !== "all" ? { status } : undefined,
      signal,
    });
  }

  getEmails({ signal } = {}) {
    return this.#request("/emails", { signal });
  }

  getCalendarEvents({ signal } = {}) {
    return this.#request("/calendar", { signal });
  }

  async #request(path, { method = "GET", body, query, signal } = {}) {
    const url = this.#createUrl(path, query);
    const headers = { Accept: "application/json" };

    if (this.profileId) {
      headers["X-Profile-Id"] = this.profileId;
    }

    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }

    let response;
    try {
      response = await this.fetchImpl(url, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
    } catch (error) {
      if (error.name === "AbortError") {
        throw error;
      }

      throw new CareerCopilotApiError(
        "Could not reach the CareerCopilot server. Make sure the API is running.",
        { details: error },
      );
    }

    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const serverMessage =
        typeof data === "object" && data !== null
          ? data.detail || data.error || data.message
          : data;

      throw new CareerCopilotApiError(
        serverMessage || `Request failed with status ${response.status}.`,
        { status: response.status, details: data },
      );
    }

    return data;
  }

  #createUrl(path, query) {
    const url = new URL(`${this.baseUrl}${path}`, globalThis.location?.origin || "http://localhost");

    for (const [key, value] of Object.entries(query || {})) {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    }

    return url;
  }
}

export const careerCopilotServer = new CareerCopilotServer({
  baseUrl: import.meta.env.VITE_API_BASE_URL || "/api",
});
