"""LangChain tool for writing final CV content to an ATS-friendly DOCX."""

import os
import re
from pathlib import Path
from typing import Annotated, Any, Literal, Type
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
    model_validator,
)

from agent.tools.base_tool import BaseTool
from agent.tools.cv_docx_renderer import (
    STANDARD_SECTION_TITLES,
    render_cv_docx,
    verify_generated_docx,
)
from agent.tools.tool_response import ToolResponse


OUTPUT_DIRECTORY = Path(__file__).resolve().parents[2] / "generated_cvs"
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
    overwrite_existing: bool = Field(default=False)


class WriteCVError(CVModel):
    field: str
    message: str


class WriteCVResult(CVModel):
    status: Literal["success", "error"]
    filename: str | None = None
    file_path: str | None = None
    sections_written: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[WriteCVError] = Field(default_factory=list)


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


def _prepare_output_paths(
    safe_filename: str, overwrite_existing: bool
) -> tuple[Path, Path]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    output_directory = OUTPUT_DIRECTORY.resolve()
    final_path = (output_directory / safe_filename).resolve()
    if final_path.parent != output_directory:
        raise CVWriteError("output_filename", "Resolved output path is unsafe")
    if final_path.exists() and not overwrite_existing:
        raise CVWriteError(
            "overwrite_existing",
            f"{safe_filename} already exists and overwrite_existing is false",
        )

    temporary_path = output_directory / (
        f".{final_path.stem}.{uuid4().hex}.temporary.docx"
    )
    return final_path, temporary_path


def _publish_document(
    temporary_path: Path,
    final_path: Path,
    overwrite_existing: bool,
) -> None:
    if overwrite_existing:
        temporary_path.replace(final_path)
        return

    try:
        os.link(temporary_path, final_path)
    except FileExistsError as error:
        raise CVWriteError(
            "overwrite_existing",
            f"{final_path.name} already exists and overwrite_existing is false",
        ) from error


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


def _validation_errors(error: ValidationError) -> list[WriteCVError]:
    errors = []
    for detail in error.errors():
        field = ".".join(str(part) for part in detail["loc"]) or "input"
        errors.append(WriteCVError(field=field, message=detail["msg"]))
    return errors


def _error_response(filename: Any, errors: list[WriteCVError]) -> ToolResponse:
    response_filename = filename if isinstance(filename, str) else None
    result = WriteCVResult(
        status="error", filename=response_filename, errors=errors
    )
    return ToolResponse(content=result.model_dump(mode="json"))


class WriteCV(BaseTool):
    name: str = "write_cv"
    description: str = (
        "Create an ATS-friendly DOCX from complete, final CV content. Provide "
        "output_filename, contact, and professional_summary. Supply every entry "
        "and bullet in its exact intended display order; dated entries should "
        "normally already be reverse chronological because this tool does not "
        "sort them. The tool also does not tailor, rewrite, improve, rank, or "
        "verify the supplied content. Use section_order when a specific section "
        "order is required."
    )
    args_schema: Type[BaseModel] = WriteCVInput

    def invoke(self, input: Any, config: Any = None, **kwargs: Any) -> Any:
        """Keep Pydantic input failures inside the tool's response contract."""
        try:
            return super().invoke(input, config=config, **kwargs)
        except ValidationError as error:
            requested_filename = (
                input.get("output_filename") if isinstance(input, dict) else None
            )
            return _error_response(requested_filename, _validation_errors(error))

    def _run(self, **kwargs) -> ToolResponse:
        temporary_path: Path | None = None
        requested_filename = kwargs.get("output_filename")
        safe_filename: str | None = None

        try:
            payload = WriteCVInput.model_validate(kwargs)
            safe_filename = _sanitize_filename(payload.output_filename)
            available_sections = _collect_available_sections(payload)
            ordered_sections, warnings = _resolve_section_order(
                payload, available_sections
            )
            final_path, temporary_path = _prepare_output_paths(
                safe_filename, payload.overwrite_existing
            )

            payload_data = payload.model_dump(mode="json")
            render_cv_docx(payload_data, ordered_sections, temporary_path)
            verify_generated_docx(temporary_path, payload_data, ordered_sections)
            _publish_document(
                temporary_path,
                final_path,
                payload.overwrite_existing,
            )
            temporary_path.unlink(missing_ok=True)
            temporary_path = None

            result = WriteCVResult(
                status="success",
                filename=safe_filename,
                file_path=str(final_path),
                sections_written=ordered_sections,
                warnings=warnings,
            )
            return ToolResponse(content=result.model_dump(mode="json"))
        except ValidationError as error:
            return _error_response(requested_filename, _validation_errors(error))
        except CVWriteError as error:
            return _error_response(
                safe_filename or requested_filename,
                [WriteCVError(field=error.field, message=error.message)],
            )
        except Exception as error:
            return _error_response(
                safe_filename or requested_filename,
                [WriteCVError(field="rendering", message=str(error))],
            )
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
