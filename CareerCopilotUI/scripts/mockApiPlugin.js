const PRIMARY_PROFILE_ID = "11111111-1111-4111-8111-111111111111";
const SECONDARY_PROFILE_ID = "22222222-2222-4222-8222-222222222222";

const profiles = [
  {
    id: PRIMARY_PROFILE_ID,
    name: "Ido Oserovitz",
    email: "ido@example.com",
    has_cv: true,
  },
  {
    id: SECONDARY_PROFILE_ID,
    name: "Yarden Demo",
    email: "yarden@example.com",
    has_cv: false,
  },
];

const applications = [
  {
    id: "a1111111-1111-4111-8111-111111111111",
    profile_id: PRIMARY_PROFILE_ID,
    job_id: "APP-7F2A",
    job_title: "Backend Intern",
    company: "Acme",
    tailored_cv_text: null,
    status: "pending",
    submitted_at: "2026-08-11T09:30:00Z",
    created_at: "2026-08-10T10:00:00Z",
  },
  {
    id: "a2222222-2222-4222-8222-222222222222",
    profile_id: PRIMARY_PROFILE_ID,
    job_id: "APP-31C9",
    job_title: "Python Developer",
    company: "Nova Labs",
    tailored_cv_text: null,
    status: "scheduled",
    submitted_at: "2026-08-09T08:00:00Z",
    created_at: "2026-08-08T08:00:00Z",
  },
  {
    id: "a3333333-3333-4333-8333-333333333333",
    profile_id: PRIMARY_PROFILE_ID,
    job_id: "APP-884D",
    job_title: "Software Intern",
    company: "Vector",
    tailored_cv_text: null,
    status: "rejected",
    submitted_at: "2026-08-04T08:00:00Z",
    created_at: "2026-08-03T08:00:00Z",
  },
];

const emails = [
  {
    id: "e1111111-1111-4111-8111-111111111111",
    application_id: applications[0].id,
    direction: "inbound",
    type: "accepted",
    subject: "Interview invitation - Backend Intern",
    body: "Hi Ido,\n\nWe were impressed by your application and would like to invite you to an interview.",
    created_at: "2026-08-11T10:00:00Z",
  },
  {
    id: "e2222222-2222-4222-8222-222222222222",
    application_id: applications[1].id,
    direction: "inbound",
    type: "confirmation",
    subject: "Interview confirmed",
    body: "Your interview is confirmed for Friday at 10:00.",
    created_at: "2026-08-10T11:00:00Z",
  },
];

const calendarEvents = [
  {
    id: "c1111111-1111-4111-8111-111111111111",
    application_id: applications[0].id,
    event_type: "interview",
    title: "Acme interview",
    description: "Backend Intern interview",
    starts_at: "2026-08-14T10:00:00+03:00",
    ends_at: "2026-08-14T10:45:00+03:00",
    status: "scheduled",
  },
  {
    id: "c2222222-2222-4222-8222-222222222222",
    application_id: applications[1].id,
    event_type: "preparation",
    title: "Interview preparation",
    description: "Review Python system design topics",
    starts_at: "2026-08-13T14:00:00+03:00",
    ends_at: "2026-08-13T15:00:00+03:00",
    status: "completed",
  },
];

let sessionCounter = 3;
const agentSessions = [
  {
    id: "b1111111-1111-4111-8111-111111111111",
    profile_id: PRIMARY_PROFILE_ID,
    title: "Prepare for the Acme interview",
    messages: [
      {
        role: "user",
        content: "Help me prepare for my next interview.",
      },
      {
        role: "assistant",
        content:
          "## Acme interview preparation\n\nFocus on these areas:\n\n- Prepare two **FastAPI** project examples\n- Review Python async patterns\n- Bring one question about the backend team",
      },
    ],
  },
  {
    id: "b2222222-2222-4222-8222-222222222222",
    profile_id: PRIMARY_PROFILE_ID,
    title: "Review my applications",
    messages: [
      {
        role: "user",
        content: "Give me a quick update on my applications.",
      },
      {
        role: "assistant",
        content:
          "You have **three active applications**. Nova Labs is already scheduled, Acme is pending, and Vector sent a rejection.",
      },
    ],
  },
];

const notifications = [
  {
    id: "d1111111-1111-4111-8111-111111111111",
    profile_id: PRIMARY_PROFILE_ID,
    title: "Interview scheduled",
    message:
      "Your Backend Software Engineer interview with Apple was scheduled for Saturday at 10:00 AM.",
    is_read: false,
    created_at: "2026-08-14T14:00:00Z",
  },
];

function sendJson(response, status, data) {
  response.statusCode = status;
  response.setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(data));
}

function activeProfile(request) {
  return request.headers["x-profile-id"] || PRIMARY_PROFILE_ID;
}

function readJson(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
    request.on("error", reject);
  });
}

function createMockSession(profileId) {
  const number = String(sessionCounter++).padStart(8, "0");
  const session = {
    id: `${number}-3333-4333-8333-333333333333`,
    profile_id: profileId,
    title: "New conversation",
    messages: [],
  };
  agentSessions.unshift(session);
  return session;
}

function titleFromPrompt(prompt) {
  const title = String(prompt || "").trim().replace(/\s+/g, " ");
  return title.length > 42 ? `${title.slice(0, 39)}…` : title || "New conversation";
}

export function careerCopilotMock() {
  return {
    name: "career-copilot-mock-api",
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        const url = new URL(request.url, "http://localhost");
        if (!url.pathname.startsWith("/api/")) {
          next();
          return;
        }

        const profileId = activeProfile(request);
        if (url.pathname === "/api/profiles") {
          sendJson(response, 200, profiles);
          return;
        }

        if (url.pathname === "/api/profile" && request.method === "GET") {
          const summary = profiles.find((profile) => profile.id === profileId) || profiles[0];
          sendJson(response, 200, {
            id: summary.id,
            name: summary.name,
            email: summary.email,
            cv_text:
              summary.id === PRIMARY_PROFILE_ID
                ? "Backend developer with Python, FastAPI, and agentic workflow experience."
                : null,
            created_at: "2026-08-01T09:00:00Z",
          });
          return;
        }

        if (url.pathname === "/api/profile/cv" && request.method === "POST") {
          sendJson(response, 200, { status: "ok" });
          return;
        }

        if (url.pathname === "/api/applications") {
          const status = url.searchParams.get("status");
          const data = profileId === PRIMARY_PROFILE_ID ? applications : [];
          sendJson(
            response,
            200,
            status ? data.filter((application) => application.status === status) : data,
          );
          return;
        }

        if (url.pathname === "/api/emails") {
          sendJson(response, 200, profileId === PRIMARY_PROFILE_ID ? emails : []);
          return;
        }

        if (url.pathname === "/api/calendar") {
          sendJson(response, 200, profileId === PRIMARY_PROFILE_ID ? calendarEvents : []);
          return;
        }

        if (url.pathname === "/api/notifications" && request.method === "GET") {
          sendJson(
            response,
            200,
            notifications.filter((notification) => notification.profile_id === profileId),
          );
          return;
        }

        if (
          url.pathname === "/api/notifications/read-all" &&
          request.method === "PATCH"
        ) {
          const updated = notifications.filter(
            (notification) =>
              notification.profile_id === profileId && !notification.is_read,
          );
          updated.forEach((notification) => {
            notification.is_read = true;
          });
          sendJson(response, 200, updated);
          return;
        }

        const notificationMatch = url.pathname.match(
          /^\/api\/notifications\/([^/]+)\/read$/,
        );
        if (notificationMatch && request.method === "PATCH") {
          const notification = notifications.find(
            (candidate) =>
              candidate.id === decodeURIComponent(notificationMatch[1]) &&
              candidate.profile_id === profileId,
          );
          if (!notification) {
            sendJson(response, 404, { detail: "Notification not found" });
            return;
          }
          notification.is_read = true;
          sendJson(response, 200, notification);
          return;
        }

        if (url.pathname === "/api/sessions" && request.method === "GET") {
          sendJson(
            response,
            200,
            agentSessions
              .filter((session) => session.profile_id === profileId)
              .map(({ id, title }) => ({ id, title })),
          );
          return;
        }

        if (url.pathname === "/api/sessions" && request.method === "POST") {
          const { id, title } = createMockSession(profileId);
          sendJson(response, 200, { id, title });
          return;
        }

        const sessionMatch = url.pathname.match(/^\/api\/sessions\/([^/]+)$/);
        if (sessionMatch && request.method === "GET") {
          const session = agentSessions.find(
            (candidate) =>
              candidate.id === decodeURIComponent(sessionMatch[1]) &&
              candidate.profile_id === profileId,
          );
          if (!session) {
            sendJson(response, 404, { detail: "Agent session not found" });
            return;
          }
          sendJson(response, 200, {
            id: session.id,
            title: session.title,
            messages: session.messages,
          });
          return;
        }

        if (url.pathname === "/api/execute" && request.method === "POST") {
          readJson(request)
            .then(({ prompt }) => {
              const shouldTrack = request.headers["x-track-session"] === "true";
              const requestedSessionId = request.headers["x-session-id"];
              let session = requestedSessionId
                ? agentSessions.find(
                    (candidate) =>
                      candidate.id === requestedSessionId && candidate.profile_id === profileId,
                  )
                : null;

              if (shouldTrack && !session) {
                session = createMockSession(profileId);
              }

              const agentResponse =
                "## Application plan\n\n- Tailor your CV for **Acme**\n- Prepare two FastAPI examples\n- Follow up on Friday";

              if (shouldTrack && session) {
                if (session.messages.length === 0) {
                  session.title = titleFromPrompt(prompt);
                }
                session.messages.push(
                  { role: "user", content: prompt },
                  { role: "assistant", content: agentResponse },
                );
                const index = agentSessions.indexOf(session);
                agentSessions.splice(index, 1);
                agentSessions.unshift(session);
              }

              if (session) {
                response.setHeader("X-Session-Id", session.id);
              }
              sendJson(response, 200, {
                status: "ok",
                error: null,
                response: agentResponse,
                steps: [
                  { module: "Job Search", prompt: {}, response: {} },
                  { module: "CV Tailoring", prompt: {}, response: {} },
                ],
              });
            })
            .catch(() => {
              sendJson(response, 400, { detail: "Invalid JSON body" });
            });
          return;
        }

        sendJson(response, 404, { detail: "Mock endpoint not found" });
      });
    },
  };
}
