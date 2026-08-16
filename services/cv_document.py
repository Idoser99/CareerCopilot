"""Create an ATS-friendly DOCX from CV content."""

import re
from io import BytesIO
from pathlib import Path
from typing import Annotated, Any, Literal, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from services.cv_docx_renderer import (
    STANDARD_SECTION_TITLES,
    render_cv_docx,
    verify_generated_docx,
)


DEFAULT_SECTION_ORDER = [
    "professional_summary",
    "education",
    "technical_skills",
    "experience",
    "projects",
    "certifications",
    "awards",
    "leadership",
    "languages",
]
STANDARD_SECTION_IDS = set(STANDARD_SECTION_TITLES)
ENTRY_SECTION_IDS = [
    "education",
    "experience",
    "projects",
    "certifications",
    "awards",
    "leadership",
]
INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
WINDOWS_RESERVED_FILENAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
COMMON_SECTION_HEADINGS = {
    "professional summary",
    "profile summary",
    "summary",
    "education",
    "experience",
    "professional experience",
    "work experience",
    "projects",
    "key projects",
    "technical skills",
    "skills",
    "certifications",
    "certifications & training",
    "awards",
    "leadership",
    "languages",
}

NonEmptyText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class CVModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ContactInformation(CVModel):
    full_name: NonEmptyText = Field(description="Candidate's full name")
    location: str | None = Field(default=None, description="City, region, or country")
    email: str | None = Field(default=None, description="Email address as display text")
    phone: str | None = Field(default=None, description="Phone number as display text")
    linkedin: str | None = Field(default=None, description="Visible LinkedIn URL")
    github: str | None = Field(default=None, description="Visible GitHub URL")
    portfolio: str | None = Field(default=None, description="Visible portfolio URL")


class CVEntry(CVModel):
    primary_text: NonEmptyText = Field(
        description="Main entry text, such as a role, degree, or project name"
    )
    secondary_text: str | None = Field(
        default=None,
        description="Organization, institution, technology summary, or other secondary text",
    )
    location: str | None = Field(default=None, description="Optional entry location")
    date: str | None = Field(
        default=None,
        description="Optional date text exactly as it should appear",
    )
    link: str | None = Field(default=None, description="Optional visible URL")
    bullets: list[NonEmptyText] = Field(
        default_factory=list,
        description="Final bullets in exact display order; the tool does not reorder them",
    )


class SkillGroup(CVModel):
    label: NonEmptyText = Field(description="Skill category label")
    items: list[NonEmptyText] = Field(
        min_length=1,
        description="Skills in exact display order",
    )


class CustomContentBlock(CVModel):
    block_type: Literal["paragraph", "labeled_text", "entry", "bullet_list"]
    text: str | None = None
    label: str | None = None
    entry: CVEntry | None = None
    bullets: list[NonEmptyText] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_renderable_content(self) -> "CustomContentBlock":
        if self.block_type == "paragraph" and not self.text:
            raise ValueError("paragraph blocks require non-empty text")
        if self.block_type == "labeled_text" and (not self.label or not self.text):
            raise ValueError("labeled_text blocks require both label and text")
        if self.block_type == "entry" and self.entry is None:
            raise ValueError("entry blocks require an entry")
        if self.block_type == "bullet_list" and not self.bullets:
            raise ValueError("bullet_list blocks require at least one bullet")
        return self


class CustomSection(CVModel):
    section_id: NonEmptyText = Field(
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Unique lowercase identifier used by section_order",
    )
    title: NonEmptyText = Field(description="Visible section title chosen by the LLM")
    blocks: list[CustomContentBlock] = Field(
        min_length=1,
        description="Renderable blocks in exact display order",
    )


class DocumentPreferences(CVModel):
    page_size: Literal["A4", "LETTER"] = Field(
        default="A4", description="A4 or US Letter page size"
    )
    font_name: Literal["Arial", "Calibri", "Aptos", "Times New Roman"] = Field(
        default="Arial", description="ATS-safe document font"
    )
    font_size_pt: float = Field(
        default=10.5,
        ge=10,
        le=12,
        description="Body font size in points",
    )
    margin_inches: float = Field(
        default=0.75,
        ge=0.5,
        le=1.25,
        description="Equal page margins in inches",
    )

    @field_validator("page_size", mode="before")
    @classmethod
    def normalize_page_size(cls, value: str) -> str:
        return value.upper() if isinstance(value, str) else value


class WriteCVInput(CVModel):
    output_filename: NonEmptyText = Field(
        description="Safe output filename; .docx is added when omitted"
    )
    contact: ContactInformation = Field(description="Candidate contact header")
    professional_summary: NonEmptyText = Field(
        description="Final professional summary; the tool writes it without rewriting"
    )
    education: list[CVEntry] = Field(
        default_factory=list,
        description="Education entries in exact display order, normally reverse chronological",
    )
    technical_skills: list[SkillGroup] = Field(default_factory=list)
    experience: list[CVEntry] = Field(
        default_factory=list,
        description=(
            "Experience entries in exact display order, normally reverse "
            "chronological; the tool does not sort"
        ),
    )
    projects: list[CVEntry] = Field(
        default_factory=list,
        description="Project entries in exact display order; the tool does not sort",
    )
    certifications: list[CVEntry] = Field(
        default_factory=list,
        description="Certification entries in exact display order",
    )
    awards: list[CVEntry] = Field(
        default_factory=list, description="Award entries in exact display order"
    )
    leadership: list[CVEntry] = Field(
        default_factory=list,
        description="Leadership entries in exact display order",
    )
    languages: list[NonEmptyText] = Field(default_factory=list)
    custom_sections: list[CustomSection] = Field(default_factory=list)
    section_order: list[NonEmptyText] | None = Field(
        default=None,
        description="Exact body-section order; must include professional_summary when supplied",
    )
    document_preferences: DocumentPreferences = Field(
        default_factory=DocumentPreferences
    )


class CVWriteError(Exception):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


def _sanitize_filename(output_filename: str) -> str:
    raw_filename = output_filename.strip()
    if "/" in raw_filename or "\\" in raw_filename or ".." in raw_filename:
        raise CVWriteError(
            "output_filename",
            "output_filename must be a filename, not a path",
        )

    suffix = Path(raw_filename).suffix
    if suffix and suffix.lower() != ".docx":
        raise CVWriteError("output_filename", "Only .docx output is supported")
    if not suffix:
        raw_filename += ".docx"

    stem = Path(raw_filename).stem
    sanitized_stem = INVALID_FILENAME_CHARACTERS.sub("_", stem).strip(" .")
    if not sanitized_stem:
        raise CVWriteError("output_filename", "output_filename is empty after sanitizing")
    if sanitized_stem.upper() in WINDOWS_RESERVED_FILENAMES:
        raise CVWriteError("output_filename", "output_filename is reserved by the system")

    return f"{sanitized_stem}.docx"


def _collect_available_sections(payload: WriteCVInput) -> dict[str, Any]:
    available: dict[str, Any] = {
        "professional_summary": payload.professional_summary,
    }
    for section_id in ENTRY_SECTION_IDS:
        content = getattr(payload, section_id)
        if content:
            available[section_id] = content
    if payload.technical_skills:
        available["technical_skills"] = payload.technical_skills
    if payload.languages:
        available["languages"] = payload.languages

    custom_ids: set[str] = set()
    for custom_section in payload.custom_sections:
        if custom_section.section_id in STANDARD_SECTION_IDS:
            raise CVWriteError(
                "custom_sections",
                f"Custom section ID conflicts with a standard section: {custom_section.section_id}",
            )
        if custom_section.section_id in custom_ids:
            raise CVWriteError(
                "custom_sections",
                f"Duplicate custom section ID: {custom_section.section_id}",
            )
        custom_ids.add(custom_section.section_id)
        available[custom_section.section_id] = custom_section

    return available


def _resolve_section_order(
    payload: WriteCVInput, available_sections: dict[str, Any]
) -> tuple[list[str], list[str]]:
    if payload.section_order is None:
        ordered = [
            section_id
            for section_id in DEFAULT_SECTION_ORDER
            if section_id in available_sections
        ]
        ordered.extend(
            section.section_id
            for section in payload.custom_sections
            if section.section_id in available_sections
        )
        return ordered, []

    ordered = payload.section_order
    if len(ordered) != len(set(ordered)):
        raise CVWriteError("section_order", "section_order contains duplicate IDs")
    if "professional_summary" not in ordered:
        raise CVWriteError(
            "section_order",
            "section_order must include professional_summary",
        )

    unknown_sections = [
        section_id for section_id in ordered if section_id not in available_sections
    ]
    if unknown_sections:
        raise CVWriteError(
            "section_order",
            "Unknown or empty section IDs: " + ", ".join(unknown_sections),
        )

    available_in_default_order = [
        section_id
        for section_id in DEFAULT_SECTION_ORDER
        if section_id in available_sections
    ]
    available_in_default_order.extend(
        section.section_id
        for section in payload.custom_sections
        if section.section_id in available_sections
    )
    omitted_sections = [
        section_id
        for section_id in available_in_default_order
        if section_id not in ordered
    ]
    warnings = []
    if omitted_sections:
        warnings.append(
            "Non-empty sections omitted by section_order: "
            + ", ".join(omitted_sections)
        )
    return ordered, warnings


def _is_section_heading(line: str) -> bool:
    letters = [character for character in line if character.isalpha()]
    return (
        bool(letters)
        and len(line) <= 60
        and (
            line == line.upper()
            or line.casefold() in COMMON_SECTION_HEADINGS
        )
        and not line.startswith(("-", "*", "•"))
    )


def _split_cv_text(cv_text: str) -> tuple[list[str], list[tuple[str, list[str]]]]:
    preamble: list[str] = []
    sections: list[tuple[str, list[str]]] = []
    current_lines: list[str] | None = None

    for raw_line in cv_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _is_section_heading(line):
            current_lines = []
            sections.append((line.title(), current_lines))
        elif current_lines is None:
            preamble.append(line)
        else:
            current_lines.append(line)

    return preamble, sections


def _build_contact(
    profile: Mapping[str, Any],
    preamble: list[str],
) -> tuple[ContactInformation, list[str]]:
    remaining = list(preamble)
    full_name = str(profile["name"])
    if remaining and "@" not in remaining[0] and len(remaining[0].split()) <= 6:
        full_name = remaining.pop(0)

    contact: dict[str, str | None] = {
        "full_name": full_name,
        "email": str(profile["email"]),
        "location": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "portfolio": None,
    }
    headline: list[str] = []
    for line in remaining:
        for value in (part.strip() for part in line.split("|")):
            lower_value = value.lower()
            if "@" in value:
                contact["email"] = value
            elif "linkedin" in lower_value:
                contact["linkedin"] = value
            elif "github" in lower_value:
                contact["github"] = value
            elif value.startswith(("http://", "https://")):
                contact["portfolio"] = value
            elif re.search(r"\+?\d[\d\s().-]{6,}", value):
                contact["phone"] = value
            elif contact["location"] is None and "," in value:
                contact["location"] = value
            else:
                headline.append(value)

    return ContactInformation.model_validate(contact), headline


def _build_custom_blocks(lines: list[str]) -> list[CustomContentBlock]:
    blocks: list[CustomContentBlock] = []
    bullets: list[str] = []

    def flush_bullets() -> None:
        if bullets:
            blocks.append(
                CustomContentBlock(block_type="bullet_list", bullets=list(bullets))
            )
            bullets.clear()

    for line in lines:
        if line.startswith(("- ", "* ", "• ")):
            bullets.append(line[2:].strip())
        else:
            flush_bullets()
            blocks.append(CustomContentBlock(block_type="paragraph", text=line))
    flush_bullets()
    return blocks


def _build_profile_payload(profile: Mapping[str, Any]) -> WriteCVInput:
    cv_text = str(profile.get("cv_text") or "").strip()
    if not cv_text:
        raise CVWriteError("cv_text", "No CV was found for this profile")

    preamble, parsed_sections = _split_cv_text(cv_text)
    contact, headline = _build_contact(profile, preamble)

    summary_titles = {"Professional Summary", "Profile Summary", "Summary"}
    summary_lines: list[str] = []
    remaining_sections: list[tuple[str, list[str]]] = []
    for title, lines in parsed_sections:
        if title in summary_titles and not summary_lines:
            summary_lines = lines
        else:
            remaining_sections.append((title, lines))

    if summary_lines:
        professional_summary = "\n".join([*headline, *summary_lines])
    elif headline:
        professional_summary = "\n".join(headline)
    else:
        professional_summary = cv_text
        remaining_sections = []

    custom_sections = [
        CustomSection(
            section_id=f"custom_{index}",
            title=title,
            blocks=_build_custom_blocks(lines),
        )
        for index, (title, lines) in enumerate(remaining_sections, start=1)
        if lines
    ]
    section_order = [
        "professional_summary",
        *(section.section_id for section in custom_sections),
    ]

    return WriteCVInput(
        output_filename=f"{contact.full_name}_CV.docx",
        contact=contact,
        professional_summary=professional_summary,
        custom_sections=custom_sections,
        section_order=section_order,
    )


def create_profile_cv_docx(profile: Mapping[str, Any]) -> tuple[BytesIO, str]:
    payload = _build_profile_payload(profile)
    filename = _sanitize_filename(payload.output_filename)
    available_sections = _collect_available_sections(payload)
    ordered_sections, _ = _resolve_section_order(payload, available_sections)
    payload_data = payload.model_dump(mode="json")

    output = BytesIO()
    render_cv_docx(payload_data, ordered_sections, output)
    output.seek(0)
    verify_generated_docx(output, payload_data, ordered_sections)
    output.seek(0)
    return output, filename


def create_application_cv_docx(
    profile: Mapping[str, Any],
    application: Mapping[str, Any],
) -> tuple[BytesIO, str]:
    """Create a DOCX from the tailored CV text saved on an application."""
    tailored_cv_text = str(application.get("tailored_cv_text") or "").strip()
    if not tailored_cv_text:
        raise CVWriteError(
            "tailored_cv_text",
            "No tailored CV draft was found for this application",
        )

    application_profile = dict(profile)
    application_profile["cv_text"] = tailored_cv_text
    output, _ = create_profile_cv_docx(application_profile)

    filename_parts = [
        profile.get("name"),
        application.get("company"),
        application.get("job_title"),
        "CV",
    ]
    filename = "_".join(
        INVALID_FILENAME_CHARACTERS.sub("_", str(part))
        .replace("..", "_")
        .strip(" ._")
        for part in filename_parts
        if part
    )
    return output, _sanitize_filename(filename)
