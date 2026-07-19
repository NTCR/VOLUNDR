"""Length analysis of the deterministic split over the full Notion + Capacities exports.

Read-only: uses the real volundr splitter + source parsers, writes nothing to any vault.

Run from the repo root:
    poetry run python length_analysis.py
"""

import statistics
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "src"))

# Fallback stubs so the script also runs on bare Python (no poetry env).
try:
    import frontmatter  # noqa: F401
except ImportError:
    import types

    import yaml

    class _Post:
        def __init__(self, metadata, content):
            self.metadata = metadata
            self.content = content

    def _fm_loads(text):
        if text.startswith("---"):
            parts = text.split("\n", 1)
            rest = parts[1] if len(parts) > 1 else ""
            end = rest.find("\n---")
            if end != -1:
                try:
                    meta = yaml.safe_load(rest[:end]) or {}
                except yaml.YAMLError:
                    meta = {}
                if isinstance(meta, dict):
                    return _Post(meta, rest[end + 4 :].lstrip("\n"))
        return _Post({}, text)

    fm = types.ModuleType("frontmatter")
    fm.loads = _fm_loads
    sys.modules["frontmatter"] = fm

try:
    from ruamel.yaml import YAML  # noqa: F401
except ImportError:
    import types

    import yaml

    class _RuamelYAML:
        def __init__(self, *a, **k):
            pass

        def load(self, stream):
            data = stream.read() if hasattr(stream, "read") else Path(stream).read_text()
            return yaml.safe_load(data)

    ruamel_pkg = types.ModuleType("ruamel")
    ruamel_yaml = types.ModuleType("ruamel.yaml")
    ruamel_yaml.YAML = _RuamelYAML
    ruamel_pkg.yaml = ruamel_yaml
    sys.modules["ruamel"] = ruamel_pkg
    sys.modules["ruamel.yaml"] = ruamel_yaml


# Same thresholds as config.yaml; config file itself is not loaded (read-only analysis).
class _Len:
    min_chars = 120
    max_chars = 6000


class _Cfg:
    length = _Len()


from volundr.splitter import split_page  # noqa: E402
from volundr.sources.notion import NotionSource  # noqa: E402
from volundr.sources.capacities import CapacitiesSource  # noqa: E402

CFG = _Cfg()

SOURCES = [
    ("notion", NotionSource(), REPO / "notion-exports"),
    ("capacities", CapacitiesSource(), REPO / "capacities-exports"),
]

BUCKETS = [(0, 50), (50, 120), (120, 300), (300, 800), (800, 2000), (2000, 6000), (6000, 10**9)]
BUCKET_LABELS = ["<50", "50-119", "120-299", "300-799", "800-1999", "2000-5999", ">=6000"]


def pct(part, whole):
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


overall_lengths = []
overall_pages = 0
overall_notes = 0

for name, src, root in SOURCES:
    if not root.exists():
        print(f"[{name}] root missing: {root}")
        continue
    files = src.discover(root)
    pages = 0
    errors = 0
    lengths = []
    line_counts = []
    notes_per_page = []
    single_note_pages = 0
    zero_note_pages = 0
    tiny_offenders = Counter()  # page title -> tiny notes
    prolific = Counter()  # page title -> notes

    for f in files:
        try:
            page = src.parse(f, root)
            notes = split_page(page, CFG)
        except Exception:
            errors += 1
            continue
        pages += 1
        notes_per_page.append(len(notes))
        if len(notes) == 0:
            zero_note_pages += 1
        if len(notes) == 1:
            single_note_pages += 1
        prolific[page.title] = len(notes)
        for n in notes:
            L = len(n.body)
            lengths.append(L)
            line_counts.append(len(n.body.splitlines()))
            if L < CFG.length.min_chars:
                tiny_offenders[page.title] += 1

    total = len(lengths)
    overall_lengths.extend(lengths)
    overall_pages += pages
    overall_notes += total

    print(f"\n{'=' * 60}\n[{name}]  {pages} pages parsed ({errors} parse errors)")
    print(f"  notes emitted: {total}  (ratio {total / pages:.2f} notes/page)" if pages else "")
    print(f"  pages -> 0 notes (empty): {zero_note_pages} | exactly 1 note: {single_note_pages} ({pct(single_note_pages, pages)})")
    if not total:
        continue
    ls = sorted(lengths)
    q = statistics.quantiles(ls, n=100)
    print(f"  body chars: min {ls[0]} | p25 {q[24]:.0f} | median {q[49]:.0f} | p75 {q[74]:.0f} | p90 {q[89]:.0f} | max {ls[-1]}")
    lc = sorted(line_counts)
    qq = statistics.quantiles(lc, n=100)
    print(f"  body lines: median {qq[49]:.0f} | p75 {qq[74]:.0f} | p90 {qq[89]:.0f} | max {lc[-1]}")
    print("  histogram (chars):")
    for (lo, hi), label in zip(BUCKETS, BUCKET_LABELS):
        c = sum(1 for L in lengths if lo <= L < hi)
        bar = "#" * round(40 * c / total)
        print(f"    {label:>9}: {c:5d} ({pct(c, total):>6}) {bar}")
    short = sum(1 for L in lengths if L < CFG.length.min_chars)
    long_ = sum(1 for L in lengths if L >= CFG.length.max_chars)
    le3 = sum(1 for c in line_counts if c <= 3)
    print(f"  flagged too_short (<{CFG.length.min_chars} chars): {short} ({pct(short, total)}) | too_long (>={CFG.length.max_chars}): {long_} ({pct(long_, total)})")
    print(f"  notes with <=3 body lines: {le3} ({pct(le3, total)})")
    npp = sorted(notes_per_page)
    print(f"  notes/page: median {npp[len(npp)//2]} | p90 {npp[int(len(npp)*0.9)]} | max {npp[-1]}")
    print("  top pages by note count:")
    for t, c in prolific.most_common(5):
        print(f"    {c:4d} notes  <- {t[:70]}")
    print("  top pages by tiny (<120 chars) notes:")
    for t, c in tiny_offenders.most_common(5):
        print(f"    {c:4d} tiny   <- {t[:70]}")

print(f"\n{'=' * 60}\nTOTAL: {overall_pages} pages -> {overall_notes} notes ({overall_notes / overall_pages:.2f} notes/page)")
short = sum(1 for L in overall_lengths if L < CFG.length.min_chars)
print(f"too_short overall: {short} ({pct(short, overall_notes)})")
