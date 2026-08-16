export class CareerCopilotApiError extends Error {
  constructor(message, { status = 0, details = null } = {}) {
    super(message);
    this.name = "CareerCopilotApiError";
    this.status = status;
    this.details = details;
  }
}

const DOCX_MEDIA_TYPE =
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

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

  getNotifications({ signal } = {}) {
    return this.#request("/notifications", { signal });
  }

  markNotificationAsRead(notificationId, { signal } = {}) {
    return this.#request(
      `/notifications/${encodeURIComponent(notificationId)}/read`,
      { method: "PATCH", signal },
    );
  }

  markAllNotificationsAsRead({ signal } = {}) {
    return this.#request("/notifications/read-all", {
      method: "PATCH",
      signal,
    });
  }

  uploadCv(cvText, { signal } = {}) {
    return this.#request("/profile/cv", {
      method: "POST",
      body: { cv_text: cvText },
      signal,
    });
  }

  downloadCv({ signal } = {}) {
    return this.#request("/profile/cv/download", {
      responseType: "blob",
      signal,
    });
  }

  execute(prompt, { sessionId = null, trackSession = false, signal } = {}) {
    return this.#request("/execute", {
      method: "POST",
      body: { prompt },
      extraHeaders: {
        "X-Track-Session": String(trackSession),
        ...(sessionId ? { "X-Session-Id": sessionId } : {}),
      },
      includeSessionId: true,
      signal,
    });
  }

  getAgentSessions({ signal } = {}) {
    return this.#request("/sessions", { signal });
  }

  createAgentSession({ signal } = {}) {
    return this.#request("/sessions", { method: "POST", signal });
  }

  getAgentSession(sessionId, { signal } = {}) {
    return this.#request(`/sessions/${encodeURIComponent(sessionId)}`, { signal });
  }

  getApplications(status = null, { signal } = {}) {
    return this.#request("/applications", {
      query: status && status !== "all" ? { status } : undefined,
      signal,
    });
  }

  downloadApplicationCv(applicationId, { signal } = {}) {
    return this.#request(
      `/applications/${encodeURIComponent(applicationId)}/cv/download`,
      {
        responseType: "blob",
        signal,
      },
    );
  }

  simulateApplicationDecision(applicationId, decision, { signal } = {}) {
    return this.#request(
      `/demo/applications/${encodeURIComponent(applicationId)}/decision`,
      {
        method: "POST",
        body: { decision },
        signal,
      },
    );
  }

  getEmails({ signal } = {}) {
    return this.#request("/emails", { signal });
  }

  getCalendarEvents({ signal } = {}) {
    return this.#request("/calendar", { signal });
  }

  async #request(
    path,
    {
      method = "GET",
      body,
      query,
      responseType = "json",
      extraHeaders = {},
      includeSessionId = false,
      signal,
    } = {},
  ) {
    const url = this.#createUrl(path, query);
    const headers = {
      Accept: responseType === "blob" ? DOCX_MEDIA_TYPE : "application/json",
    };

    if (this.profileId) {
      headers["X-Profile-Id"] = this.profileId;
    }

    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    Object.assign(headers, extraHeaders);

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
    const data = response.ok && responseType === "blob"
      ? await response.blob()
      : contentType.includes("application/json")
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

    if (responseType === "blob") {
      const disposition = response.headers.get("content-disposition") || "";
      const encodedFilename = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
      return {
        blob: data,
        filename: encodedFilename ? decodeURIComponent(encodedFilename) : "cv.docx",
      };
    }

    if (includeSessionId && typeof data === "object" && data !== null) {
      return {
        ...data,
        session_id: response.headers.get("X-Session-Id"),
      };
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
