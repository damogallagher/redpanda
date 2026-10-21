"""Extract text from MediaWiki table diffs; unsupported structures fail closed."""

from collections.abc import Iterator
from html.parser import HTMLParser

from triage.limits import MAX_TEXT_CHARS
from triage.schema import MAX_REASONING_HUNKS, Evidence

MAX_HTML_DEPTH = 16  # Normal table diffs are shallow; bound hostile nesting.
MIN_SIDE_CELLS = 2  # Marker followed by the text cell (except the empty placeholder).

ROLES = {
    "diff-lineno",
    "diff-marker",
    "diff-empty",
    "diff-context",
    "diff-deletedline",
    "diff-addedline",
}


class DiffParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.rows: list[list[tuple[str, str]]] = []
        self.cells: list[tuple[str, str]] = []
        self.role = ""
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.stack) >= MAX_HTML_DEPTH:
            raise ValueError("diff nesting exceeds limit")
        if tag == "tr" and not self.stack:
            self.cells = []
        elif tag == "td" and self.stack == ["tr"]:
            roles = set((dict(attrs).get("class") or "").split()) & ROLES
            if len(roles) != 1:
                raise ValueError("unknown diff cell")
            self.role = roles.pop()
            self.parts = []
        elif tag in {"div", "ins", "del", "span", "a", "br"} and "td" in self.stack:
            if tag == "br":
                self.parts.append("\n")
                return
        else:
            raise ValueError("unsupported diff structure")
        self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "br":
            raise ValueError("unsupported self-closing tag")
        self.handle_starttag(tag, attrs)

    def handle_comment(self, data: str) -> None:
        raise ValueError("unexpected HTML comment")

    def handle_decl(self, decl: str) -> None:
        raise ValueError("unexpected HTML declaration")

    def handle_pi(self, data: str) -> None:
        raise ValueError("unexpected processing instruction")

    def unknown_decl(self, data: str) -> None:
        raise ValueError("unexpected declaration")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack.pop() != tag:
            raise ValueError("unbalanced diff")
        if tag == "td":
            self.cells.append((self.role, "".join(self.parts)))
        elif tag == "tr":
            self.rows.append(self.cells)

    def handle_data(self, data: str) -> None:
        if "td" in self.stack:
            self.parts.append(data)
        elif data.strip():
            raise ValueError("text outside diff cells")


def side(cells: list[tuple[str, str]], changed_role: str) -> tuple[str, str]:
    if cells and cells[0][0] == "diff-empty":
        role, text = cells.pop(0)
        if text:
            raise ValueError("nonempty placeholder")
        return role, text
    if len(cells) < MIN_SIDE_CELLS or cells.pop(0)[0] != "diff-marker":
        raise ValueError("missing diff marker")
    role, text = cells.pop(0)
    if role not in {"diff-context", changed_role}:
        raise ValueError("wrong diff direction")
    return role, text


def text_hunks(rows: list[list[tuple[str, str]]]) -> Iterator[tuple[str, str]]:
    before: list[str] = []
    after: list[str] = []
    started = False
    for row in rows:
        if [role for role, _ in row] == ["diff-lineno", "diff-lineno"]:
            if started:
                yield "\n".join(before), "\n".join(after)
            before, after = [], []
            started = True
            continue
        if not started:
            raise ValueError("missing hunk header")
        left_role, old = side(row, "diff-deletedline")
        right_role, new = side(row, "diff-addedline")
        if row:
            raise ValueError("extra diff cells")
        if "diff-context" in {left_role, right_role} and (left_role != right_role or old != new):
            raise ValueError("inconsistent context")
        if left_role != "diff-empty":
            before.append(old)
        if right_role != "diff-empty":
            after.append(new)
    yield "\n".join(before), "\n".join(after)


def extract_evidence(body: str, total_limit: int) -> tuple[tuple[Evidence, ...], bool]:
    if not body.strip():
        return (), False
    parser = DiffParser()
    parser.feed(body)
    parser.close()
    if parser.stack or not parser.rows:
        raise ValueError("incomplete diff")
    evidence: list[Evidence] = []
    total = 0
    truncated = False
    for old, new in text_hunks(parser.rows):
        if old == new:
            raise ValueError("nonempty diff without an extractable change")
        size = len(old) + len(new)
        if (
            len(old) > MAX_TEXT_CHARS
            or len(new) > MAX_TEXT_CHARS
            or total + size > total_limit
            or len(evidence) >= MAX_REASONING_HUNKS
        ):
            truncated = True
        else:
            evidence.append(Evidence(before=old, after=new))
            total += size
    return tuple(evidence), truncated
