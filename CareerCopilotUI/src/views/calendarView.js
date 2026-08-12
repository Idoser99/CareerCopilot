import { Calendar } from "fullcalendar";
import listPlugin from "fullcalendar/list";
import timeGridPlugin from "fullcalendar/timegrid";
import {
  escapeHtml,
  formatTimeRange,
  renderEmpty,
  renderLoading,
  statusClass,
} from "../ui/sharedComponents.js";

function sortEvents(events) {
  return [...events].sort(
    (first, second) => new Date(first.starts_at) - new Date(second.starts_at),
  );
}

function renderAgenda(events) {
  if (events.length === 0) {
    return renderEmpty("No calendar events", "Scheduled interviews and reminders will appear here.");
  }

  return `
    <ol class="agenda-list">
      ${events
        .map(
          (event) => `
            <li class="agenda-item">
              <div class="agenda-date-mark" aria-hidden="true">
                <span>${escapeHtml(
                  new Intl.DateTimeFormat(undefined, { month: "short" }).format(
                    new Date(event.starts_at),
                  ),
                )}</span>
                <strong>${escapeHtml(
                  new Intl.DateTimeFormat(undefined, { day: "numeric" }).format(
                    new Date(event.starts_at),
                  ),
                )}</strong>
              </div>
              <div class="agenda-copy">
                <div class="agenda-title-row">
                  <h3>${escapeHtml(event.title)}</h3>
                  <span class="status-pill ${statusClass(event.status)}">${escapeHtml(event.status)}</span>
                </div>
                <p class="agenda-time">${escapeHtml(formatTimeRange(event.starts_at, event.ends_at))}</p>
                ${event.description ? `<p>${escapeHtml(event.description)}</p>` : ""}
                <span class="mono-text">Application ${escapeHtml(event.application_id)}</span>
              </div>
            </li>
          `,
        )
        .join("")}
    </ol>
  `;
}

export async function renderCalendarView(container, { server, signal }) {
  container.innerHTML = `
    <section class="page-heading">
      <div>
        <p class="eyebrow">Calendar</p>
        <h1>Interviews, automatically scheduled</h1>
        <p class="page-subtitle">See every event chronologically or switch to a weekly calendar.</p>
      </div>
    </section>
    ${renderLoading("Loading calendar events…")}
  `;

  const response = await server.getCalendarEvents({ signal });
  if (signal.aborted) return undefined;

  const events = sortEvents(Array.isArray(response) ? response : []);
  container.innerHTML = `
    <section class="page-heading page-heading--with-control">
      <div>
        <p class="eyebrow">Calendar</p>
        <h1>Interviews, automatically scheduled</h1>
        <p class="page-subtitle">See every event chronologically or switch to a weekly calendar.</p>
      </div>
      <div class="segmented-control" role="group" aria-label="Calendar view">
        <button class="is-active" type="button" data-calendar-view="agenda">Agenda</button>
        <button type="button" data-calendar-view="week">Week</button>
      </div>
    </section>

    <section class="card calendar-card">
      <div id="agenda-view">${renderAgenda(events)}</div>
      <div id="week-view" class="is-hidden">
        <div id="full-calendar"></div>
      </div>
    </section>
  `;

  const agendaView = container.querySelector("#agenda-view");
  const weekView = container.querySelector("#week-view");
  const calendarElement = container.querySelector("#full-calendar");
  const controls = [...container.querySelectorAll("[data-calendar-view]")];

  const calendar = new Calendar(calendarElement, {
    plugins: [timeGridPlugin, listPlugin],
    initialView: "timeGridWeek",
    initialDate: events[0]?.starts_at,
    height: "auto",
    nowIndicator: true,
    allDaySlot: false,
    slotMinTime: "07:00:00",
    slotMaxTime: "21:00:00",
    expandRows: true,
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridWeek,timeGridDay",
    },
    buttonText: {
      today: "Today",
      week: "Week",
      day: "Day",
    },
    events: events.map((event) => ({
      id: event.id,
      title: event.title,
      start: event.starts_at,
      end: event.ends_at,
      classNames: [`calendar-event--${String(event.status || "scheduled").toLowerCase()}`],
      extendedProps: {
        applicationId: event.application_id,
        description: event.description,
        status: event.status,
      },
    })),
  });

  let calendarRendered = false;
  for (const control of controls) {
    control.addEventListener("click", () => {
      const selectedView = control.dataset.calendarView;
      controls.forEach((button) => button.classList.toggle("is-active", button === control));
      agendaView.classList.toggle("is-hidden", selectedView !== "agenda");
      weekView.classList.toggle("is-hidden", selectedView !== "week");

      if (selectedView === "week") {
        if (!calendarRendered) {
          calendar.render();
          calendarRendered = true;
        } else {
          calendar.updateSize();
        }
      }
    });
  }

  return () => {
    if (calendarRendered) calendar.destroy();
  };
}
