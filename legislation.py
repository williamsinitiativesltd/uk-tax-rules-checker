"""Read sections of saved Crown Legislation Markup Language (CLML)."""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

L = "{http://www.legislation.gov.uk/namespaces/legislation}"
X = "{http://www.w3.org/1999/xhtml}"
M = "{http://www.legislation.gov.uk/namespaces/metadata}"
ATOM = "{http://www.w3.org/2005/Atom}"


def words(node):
    # Inline markup can split a word or separate it from its punctuation.
    return " ".join("".join(node.itertext()).split())


@dataclass
class Section:
    number: str
    heading: str
    start: date
    end: date | None  # Exclusive, as in RestrictEndDate.
    versions: list[date]
    commentaries: dict[str, str]
    unapplied: int
    group: ET.Element

    def subsection(self, number):
        return next((p for p in self.group.iter(L + "P2")
                     if words(p.find(L + "Pnumber")) == number), None)

    def referenced_commentaries(self):
        refs = {el.get("CommentaryRef") for el in self.group.iter()}
        refs.update(el.get("Ref") for el in self.group.iter(L + "CommentaryRef"))
        return [note for key, note in self.commentaries.items() if key in refs]


def read_xml(path):
    return ET.parse(path).getroot()


def load(path, read=read_xml) -> Section:
    root = read(path)
    group, = root.iter(L + "P1group")
    provision = group.find(L + "P1")
    # A whole Act's validity date can change while this section stays in force.
    start = (provision.get("RestrictStartDate") or group.get("RestrictStartDate")
             or root.findtext(".//{http://purl.org/dc/terms/}valid")
             or root.findtext(".//{http://purl.org/dc/elements/1.1/}valid"))
    if not start:
        raise ValueError(f"No section start date in {path}")
    end = provision.get("RestrictEndDate") or group.get("RestrictEndDate")
    versions = []
    for link in root.iter(ATOM + "link"):
        if link.get("rel", "").endswith("/hasVersion"):
            version = link.attrib["href"].rstrip("/").rsplit("/", 1)[-1]
            if link.get("title") != "current" and version != "enacted":
                versions.append(date.fromisoformat(version))
    return Section(
        words(provision.find(L + "Pnumber")), words(group.find(L + "Title")),
        date.fromisoformat(start), date.fromisoformat(end) if end else None, versions,
        {el.attrib["id"]: words(el) for el in root.iter(L + "Commentary")},
        len(root.findall(f".//{M}UnappliedEffects/{M}UnappliedEffect")), group,
    )


@dataclass
class Cell:
    text: str
    refs: tuple[str, ...]


@dataclass
class Table:
    caption: str
    headers: list[list[Cell]]
    rows: list[list[Cell]]


def tables(section: Section, subsection=None) -> list[Table]:
    scope = section.group if subsection is None else section.subsection(subsection)
    if scope is None:
        return []
    parents = {child: parent for parent in section.group.iter() for child in parent}

    def ancestors(node):
        while node in parents:
            node = parents[node]
            yield node

    def cell(node):
        refs = dict.fromkeys(el.attrib["CommentaryRef"]
                             for el in (*reversed(list(ancestors(node))), *node.iter())
                             if el.tag in (L + "Substitution", L + "Addition") and "CommentaryRef" in el.attrib)
        return Cell(words(node), tuple(refs))

    result = []
    for element in scope.iter(X + "table"):
        captions = element.findall(X + "caption")
        wrapper = next((p for p in ancestors(element) if p.tag == L + "Tabular"), None)
        if wrapper is not None:
            captions += [el for el in wrapper if el.tag in (L + "Number", L + "Title")]
        table = Table(" ".join(map(words, captions)), [], [])
        for row in element.iter(X + "tr"):
            lineage = list(ancestors(row))
            if next(p for p in lineage if p.tag == X + "table") is not element:
                continue
            cells = [el for el in row if el.tag in (X + "td", X + "th")]
            header = any(p.tag == X + "thead" for p in lineage) or all(el.tag == X + "th" for el in cells)
            (table.headers if header else table.rows).append([cell(el) for el in cells])
        result.append(table)
    return result


def text(section: Section) -> str:
    """Keep block boundaries and printed provision numbers when flattening inline text."""
    def flatten(node):
        if node.tag == L + "Pnumber":
            number = words(node)
            return number + "\n" if node.get("PuncAfter") == "" else f"({number})\n"
        parts = [node.text or ""]
        for child in node:
            parts.extend((flatten(child), child.tail or ""))
        if node.tag in (L + "Text", L + "Title", L + "Number", X + "td", X + "th"):
            return "\n" + "".join(parts) + "\n"
        return "".join(parts)

    return "\n".join(" ".join(line.split()) for line in flatten(section.group).splitlines() if line.strip())
