import DOMPurify from "dompurify";
import { marked } from "marked";

marked.setOptions({
  breaks: true,
  gfm: true,
});

export function renderMarkdown(container, markdown) {
  const source = String(markdown || "").replace(
    /^[\u200B\u200C\u200D\u200E\u200F\uFEFF]/,
    "",
  );
  const rendered = marked.parse(source);
  container.innerHTML = DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ["style"],
    FORBID_ATTR: ["style"],
  });
}
