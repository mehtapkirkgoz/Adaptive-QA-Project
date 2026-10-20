"""Page-scoped feature detection from value-free discovery snapshots."""

import unicodedata
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from adaptive_qa.config import extract_hostname
from adaptive_qa.models import FeatureStatus


def _text_fields(**values: str) -> None:
    if any(not isinstance(value, str) for value in values.values()):
        raise ValueError("Snapshot text fields must be strings.")


def _typed_tuple(value: tuple, item_type: type, name: str) -> None:
    if not isinstance(value, tuple) or any(not isinstance(item, item_type) for item in value):
        raise ValueError(f"{name} must be a tuple of {item_type.__name__} values.")


@dataclass(frozen=True)
class FieldSnapshot:
    input_type: str = "text"
    label: str = ""
    autocomplete: str = ""
    visible: bool = True

    def __post_init__(self) -> None:
        _text_fields(input_type=self.input_type, label=self.label, autocomplete=self.autocomplete)
        if not isinstance(self.visible, bool):
            raise ValueError("visible must be a bool.")


@dataclass(frozen=True)
class FormSnapshot:
    form_id: str = ""
    role: str = ""
    fields: tuple[FieldSnapshot, ...] = ()
    buttons: tuple[str, ...] = ()
    visible: bool = True

    def __post_init__(self) -> None:
        _text_fields(form_id=self.form_id, role=self.role)
        _typed_tuple(self.fields, FieldSnapshot, "fields")
        _typed_tuple(self.buttons, str, "buttons")
        if not isinstance(self.visible, bool):
            raise ValueError("visible must be a bool.")


@dataclass(frozen=True)
class LinkSnapshot:
    text: str
    href: str

    def __post_init__(self) -> None:
        _text_fields(text=self.text, href=self.href)


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    forms: tuple[FormSnapshot, ...] = ()
    links: tuple[LinkSnapshot, ...] = ()
    collection_complete: bool = False

    def __post_init__(self) -> None:
        extract_hostname(self.url)
        _typed_tuple(self.forms, FormSnapshot, "forms")
        _typed_tuple(self.links, LinkSnapshot, "links")
        if not isinstance(self.collection_complete, bool):
            raise ValueError("collection_complete must be a bool.")


@dataclass(frozen=True)
class FeatureFinding:
    feature: str
    page_url: str
    status: FeatureStatus
    reason: str
    evidence: tuple[str, ...] = ()
    scope: str = field(default="page", init=False)


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold()).replace("ı", "i")
    return " ".join("".join(
        character if character.isalnum() else " "
        for character in value if not unicodedata.combining(character)
    ).split())


_LOGIN_NAMES = {"login", "log in", "sign in", "giris yap", "oturum ac"}
_SEARCH_NAMES = {"search", "search products", "ara", "urun ara"}


def detect_page_features(snapshot: PageSnapshot) -> tuple[FeatureFinding, ...]:
    """Detect visible login/search features; absence applies only to this page."""
    if not isinstance(snapshot, PageSnapshot):
        raise ValueError("snapshot must be a PageSnapshot instance.")
    present: dict[str, str] = {}
    hints: dict[str, list[str]] = {"login": [], "search": []}
    for index, form in enumerate(snapshot.forms):
        if not form.visible:
            continue
        reference = f"form[{index}]"
        fields = [item for item in form.fields if item.visible]
        types = {item.input_type.casefold() for item in fields}
        buttons = {_normalize(button) for button in form.buttons if button.strip()}
        if buttons & _LOGIN_NAMES:
            hints["login"].append(reference + ": login action")
        if buttons & _SEARCH_NAMES:
            hints["search"].append(reference + ": search action")
        if "password" in types:
            hints["login"].append(reference + ": password field")
            current_password = any(
                item.input_type.casefold() == "password"
                and "new-password" not in item.autocomplete.casefold().split()
                for item in fields
            )
            if current_password and types & {"text", "email", "tel"} and buttons & _LOGIN_NAMES:
                present.setdefault("login", reference)
        query = "search" in types or (form.role.casefold() == "search" and "text" in types)
        if query:
            hints["search"].append(reference + ": query field")
            if buttons & _SEARCH_NAMES or (form.role.casefold() == "search" and buttons):
                present.setdefault("search", reference)

    for index, link in enumerate(snapshot.links):
        labels = {_normalize(link.text)}
        try:
            parsed = urlsplit(link.href)
            labels.add(_normalize(parsed.path.rstrip("/").rsplit("/", 1)[-1]))
            labels.add(_normalize(parsed.fragment))
        except ValueError:
            continue
        if labels & (_LOGIN_NAMES | {"giris"}):
            hints["login"].append(f"link[{index}]: login hint")
        if labels & _SEARCH_NAMES:
            hints["search"].append(f"link[{index}]: search hint")

    findings = []
    for feature in ("login", "search"):
        if feature in present:
            status = FeatureStatus.PRESENT
            reason = "Visible form fields and action semantics match the feature."
            evidence = (present[feature],)
        elif hints[feature]:
            status = FeatureStatus.UNKNOWN
            reason = "Partial evidence requires further inspection or navigation."
            evidence = tuple(hints[feature])
        elif not snapshot.collection_complete:
            status = FeatureStatus.UNKNOWN
            reason = "Page collection is incomplete; absence cannot be established."
            evidence = ()
        else:
            status = FeatureStatus.ABSENT
            reason = "No visible matching evidence on this inspected page; not site-wide absence."
            evidence = ()
        findings.append(FeatureFinding(feature, snapshot.url, status, reason, evidence))
    return tuple(findings)
