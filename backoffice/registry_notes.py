"""Why a series is inactive, as documented in git (registry/unmapped-*.md, spec G4).

The files are free-form markdown written per source (tables, bullets, prose), so no reason is
extracted or paraphrased: a series' notes are the verbatim lines that name its id as an exact
token, each with its file and the section heading above it. Deterministic and cheap: read
once at startup.
"""
import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN = re.compile(r"[A-Za-z0-9_.]+")


@dataclass(frozen=True)
class Note:
    file: str     # e.g. unmapped-eurostat.md
    section: str  # nearest markdown heading above the line ('' before the first one)
    text: str     # the line, verbatim (stripped)


def inactive_notes(registry_dir: Path, ids: set[str]) -> dict[str, list[Note]]:
    """{series id: notes} for the ids in `ids` that some unmapped-*.md line names."""
    notes: dict[str, list[Note]] = {}
    for path in sorted(Path(registry_dir).glob("unmapped-*.md")):
        section = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                section = line.lstrip("#").strip()
                continue
            named = {t.rstrip(".") for t in _TOKEN.findall(line)} & ids
            for sid in sorted(named):
                notes.setdefault(sid, []).append(Note(path.name, section, line.strip()))
    return notes
