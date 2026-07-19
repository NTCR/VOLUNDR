"""Stage 2: Bootstrap tag vocabulary from the inbox drafts.

Extracts tag candidates using 4 extractors (human tags, headings/titles,
TF-IDF, and local LLM), normalises and filters them, and outputs a frequency
table to ``_META/harvest/tags_frequency.md``.
"""

from __future__ import annotations

import json
import math
import re
import sys
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path

from volundr.config import Config
from volundr.models import SourcePage
from volundr.sources.base import discover_markdown, extract_notion_id
from volundr.sources.capacities import CapacitiesSource
from volundr.sources.notion import NotionSource, ManualSource

# English and Spanish stop words, plus common PKM/markdown boilerplate words
STOP_WORDS = {
    # English
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant", "cannot", "could",
    "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during", "each", "few", "for", "from",
    "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill", "im", "ive", "if", "in",
    "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more", "most", "mustnt", "my", "myself", "no", "nor",
    "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shant", "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than",
    "that", "thats", "the", "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they",
    "theyd", "thell", "theyre", "theyve", "this", "those", "through", "to", "too", "under", "until", "up", "very",
    "was", "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", "whats", "when", "where", "wheres",
    "which", "while", "who", "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd",
    "youll", "youre", "youve", "your", "yours", "yourself", "yourselves",
    # Spanish
    "el", "la", "los", "les", "un", "una", "unos", "unas", "y", "o", "pero", "para", "por", "con", "de", "del", "al",
    "en", "su", "sus", "mi", "mis", "tu", "tus", "que", "qué", "como", "cómo", "es", "son", "era", "eran", "fue",
    "fueron", "he", "ha", "han", "hay", "tener", "tiene", "tienen", "todo", "todos", "parte", "partes", "este",
    "esta", "esto", "estos", "estas", "ese", "esa", "eso", "esos", "esas", "aquel", "aquella", "aquello", "aquellos",
    "aquellas", "yo", "tú", "él", "ella", "nosotros", "vosotros", "ellos", "ellas", "me", "te", "se", "nos", "os",
    "le", "lo", "las", "les",
    # PKM/Metadata words to ignore
    "note", "notes", "page", "pages", "draft", "drafts", "text", "content", "file", "files", "link", "links", "todo"
}


def normalize_tag(text: str) -> str:
    """Normalize text to lowercase, singular, kebab-case tag."""
    # Lowercase & strip spaces
    text = text.lower().strip()
    # Replace common spanish accented characters
    accents = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n"}
    for acc, rep in accents.items():
        text = text.replace(acc, rep)
    # Replace spaces, slashes, underscores, and hashtags with hyphens
    text = re.sub(r'[\s_\/\\:\#\^\[\]\|,\.\!\?\(\)\+]+', '-', text)
    # Keep only lowercase letters, numbers, and hyphens
    text = re.sub(r'[^a-z0-9\-]', '', text)
    # Deduplicate hyphens and strip leading/trailing hyphens
    text = re.sub(r'-+', '-', text).strip('-')
    
    if not text:
        return ""
        
    # Heuristic singularization
    if '-' in text:
        parts = text.split('-')
        parts[-1] = _singularize_word(parts[-1])
        text = '-'.join(parts)
    else:
        text = _singularize_word(text)
        
    return text


def _singularize_word(word: str) -> str:
    """Apply basic heuristics to singularise a single English/Spanish word."""
    exceptions = {
        # General/tech exceptions
        "class", "process", "status", "basis", "focus", "physics", "analysis",
        "hypothesis", "diagnosis", "chaos", "lens", "news", "series", "species",
        "kubernetes", "os", "js", "ts", "css", "dns", "postgres", "redis", "alias", "pkm", "mes"
    }
    if word in exceptions:
        return word
        
    # Check if stripping 'es' yields a known exception (e.g. meses -> mes, processes -> process)
    if word.endswith("es") and len(word) > 3:
        if word[:-2] in exceptions:
            return word[:-2]
        
    # If plural form of a known -sis exception (e.g. analyses -> analysis, bases -> basis)
    if word.endswith("ses") and len(word) > 4:
        potential_singular = word[:-3] + "sis"
        if potential_singular in exceptions:
            return potential_singular
    
    # Spanish singularization rules:
    # If ends in 'es', look at the character before. E.g. 'papeles' -> 'papel', 'meses' -> 'mes'
    if word.endswith("es") and len(word) > 4:
        # If preceding is 'c', it might be 'ces' -> 'z' (e.g. 'actrices' -> 'actriz')
        if word.endswith("ces"):
            return word[:-3] + "z"
        # If preceding is a consonant (r, n, d, z, s, etc.), strip 'es'
        # e.g., 'motores' -> 'motor', 'ciudades' -> 'ciudad'
        if word[-3] in "rndz":
            return word[:-2]
            
    # English/Spanish rules:
    # If ends in 'ies', change to 'y' (e.g. 'dependencies' -> 'dependency', 'categories' -> 'category')
    if word.endswith("ies") and len(word) > 3:
        return word[:-3] + "y"
        
    # If ends in 'es' after 'sh', 'ch', 'x', 's', 'z'
    if word.endswith("es") and len(word) > 4:
        for suffix in ("ches", "shes", "xes", "zes", "sses"):
            if word.endswith(suffix):
                return word[:-2]
                
    # General: ends in 's' but not 'ss' (and longer than 2 letters)
    if word.endswith("s") and not word.endswith("ss") and len(word) > 2:
        return word[:-1]
        
    return word


def extract_from_headings(page: SourcePage) -> list[str]:
    """Extractor 2: Extract words/phrases from document title and section headings."""
    candidates: list[str] = []
    
    # Extract from title
    candidates.extend(_extract_words_from_text(page.title))
    
    # Extract from headings in raw_body
    for line in page.raw_body.splitlines():
        line = line.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            # If the heading is short (1 or 2 words), extract the entire normalized phrase as a candidate
            words = heading.split()
            if 1 <= len(words) <= 2:
                phrase = normalize_tag(heading)
                if phrase and phrase not in STOP_WORDS:
                    candidates.append(phrase)
            candidates.extend(_extract_words_from_text(heading))
            
    return candidates


def _extract_words_from_text(text: str) -> list[str]:
    """Helper to split heading/title text into valid normalised words."""
    words = re.split(r'[\s_\/\\:\#\^\[\]\|,\.\!\?\(\)\-\+`]+', text)
    valid_words = []
    for word in words:
        norm = normalize_tag(word)
        # Avoid extremely short words and stop words
        if norm and len(norm) >= 3 and norm not in STOP_WORDS:
            valid_words.append(norm)
    return valid_words


def extract_tfidf(pages: list[SourcePage], top_k: int = 5) -> dict[Path, list[str]]:
    """Extractor 3: Extract top_k TF-IDF words for each document."""
    doc_terms: dict[Path, list[str]] = {}
    df_counter: Counter = Counter()
    
    for page in pages:
        text = f"{page.title}\n{page.raw_body}"
        words = re.split(r'[\s_\/\\:\#\^\[\]\|,\.\!\?\(\)\-\+\*`]+', text)
        terms = []
        for w in words:
            norm = normalize_tag(w)
            if norm and len(norm) >= 3 and norm not in STOP_WORDS:
                terms.append(norm)
        
        doc_terms[page.path] = terms
        for unique_term in set(terms):
            df_counter[unique_term] += 1
            
    results: dict[Path, list[str]] = {}
    N = len(pages)
    if N == 0:
        return {}
        
    for page in pages:
        terms = doc_terms[page.path]
        if not terms:
            results[page.path] = []
            continue
            
        tf = Counter(terms)
        tf_idf_scores = {}
        for term, count in tf.items():
            term_tf = count / len(terms)
            term_df = df_counter[term]
            # TF-IDF formula with smoothing to avoid log(0) and division issues
            idf = math.log((N + 1) / term_df)
            tf_idf_scores[term] = term_tf * idf
            
        sorted_terms = sorted(tf_idf_scores.keys(), key=lambda t: tf_idf_scores[t], reverse=True)
        results[page.path] = sorted_terms[:top_k]
        
    return results


def query_ollama_for_tags(
    endpoint: str, model: str, title: str, content: str
) -> list[str]:
    """Extractor 4: Ask local Ollama server to suggest up to 5 relevant tags."""
    url = f"{endpoint.rstrip('/')}/api/chat"
    
    # Restrict content length to avoid massive prompt sizes
    truncated_content = content[:3000]
    
    prompt = (
        "You are a Personal Knowledge Management (PKM) tagging assistant.\n"
        f"Analyze this document titled '{title}' and suggest up to 5 highly relevant tags.\n"
        "Rules:\n"
        "1. Output tags in English.\n"
        "2. Tags must be lowercase, singular, and use kebab-case for compound terms (e.g. 'game-development', 'python').\n"
        "3. Focus on core topics, technologies, and concepts. Avoid generic terms like 'note', 'article', 'general'.\n\n"
        f"Document Content:\n{truncated_content}"
    )
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": { "type": "string" }
                }
            },
            "required": ["tags"]
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            content_str = res_json["message"]["content"]
            content_data = json.loads(content_str)
            raw_tags = content_data.get("tags", [])
            
            normalized = []
            for tag in raw_tags:
                norm = normalize_tag(tag)
                if norm and norm not in STOP_WORDS:
                    normalized.append(norm)
            return normalized
    except (urllib.error.URLError, OSError) as e:
        # Surface connection/timeout error quietly in background, captured by caller
        raise ConnectionError(f"Ollama connection failed: {e}")
    except Exception as e:
        raise ValueError(f"Ollama parsing failed: {e}")


def detect_and_parse(path: Path, root: Path) -> SourcePage:
    """Auto-detect the appropriate parser for a draft markdown file and parse it."""
    # 1. Notion check: stem has a 32-hex ID
    if extract_notion_id(path.stem) is not None:
        return NotionSource().parse(path, root)
        
    # Read first lines to check for YAML frontmatter
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        raise ValueError(f"Failed to read file {path.name}: {exc}")
        
    if content.startswith("---"):
        # If path contains "capacities", parse as capacities. Otherwise manual source supports it too.
        path_parts = [p.lower() for p in path.parts]
        if any("capacities" in part for part in path_parts):
            return CapacitiesSource().parse(path, root)
        else:
            return ManualSource().parse(path, root)
    else:
        return ManualSource().parse(path, root)


def harvest_inbox(config: Config, source_filter: str | None = None) -> dict[str, dict[str, int]]:
    """Scan 0_INBOX/, extract tag candidates from all 4 sources, aggregate and save report.

    Returns the tag frequency data mapping: tag -> {source_type -> count}.
    """
    inbox = config.vault_path / "0_INBOX"
    harvest_dir = config.vault_path / "_META/harvest"
    harvest_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Discover all draft files
    all_paths = discover_markdown(inbox)
    
    # If source_filter is specified, filter files whose parsed source matches it
    # We first parse files to filter, or check by path convention
    parsed_pages: list[SourcePage] = []
    
    # Standard output stream writer for interactive progress updates
    sys.stdout.write(f"Discovering and parsing markdown drafts in {inbox}...\n")
    sys.stdout.flush()
    
    for idx, path in enumerate(all_paths):
        try:
            page = detect_and_parse(path, inbox)
            if source_filter and page.source != source_filter:
                continue
            parsed_pages.append(page)
        except Exception as exc:
            sys.stdout.write(f"[WARNING] Skipping {path.name}: parse error ({exc})\n")
            sys.stdout.flush()
            
    total_docs = len(parsed_pages)
    sys.stdout.write(f"Found {total_docs} drafts to process.\n")
    sys.stdout.flush()
    
    if total_docs == 0:
        sys.stdout.write("No drafts found to harvest.\n")
        return {}
        
    # 2. Check if Ollama is accessible
    ollama_ok = True
    try:
        # Check /api/tags or make a minimal call to ensure it responds
        url = f"{config.ollama_endpoint.rstrip('/')}/api/tags"
        with urllib.request.urlopen(url, timeout=3) as _:
            pass
    except Exception:
        sys.stdout.write(
            f"[WARNING] Ollama server not reachable at {config.ollama_endpoint}.\n"
            "Skipping Extractor 4 (LLM free-taging) and harvesting with the remaining 3 extractors.\n\n"
        )
        sys.stdout.flush()
        ollama_ok = False

    # 3. Compute TF-IDF candidates first (needs full corpus)
    tfidf_candidates = extract_tfidf(parsed_pages, top_k=5)
    
    # 4. Extract candidates per document
    # Structure: tag -> { "human": count, "headings": count, "tfidf": count, "llm": count, "total": count }
    frequencies = defaultdict(lambda: Counter())
    
    for i, page in enumerate(parsed_pages, 1):
        sys.stdout.write(f"Processing [{i}/{total_docs}]: {page.title}\n")
        sys.stdout.flush()
        
        # Extractor 1: Human tags
        for tag in page.tags:
            norm = normalize_tag(tag)
            if norm and norm not in STOP_WORDS:
                frequencies[norm]["human"] += 1
                frequencies[norm]["total"] += 1
                
        # Extractor 2: Headings/Titles
        headings_tags = extract_from_headings(page)
        for tag in headings_tags:
            frequencies[tag]["headings"] += 1
            frequencies[tag]["total"] += 1
            
        # Extractor 3: TF-IDF
        page_tfidf = tfidf_candidates.get(page.path, [])
        for tag in page_tfidf:
            frequencies[tag]["tfidf"] += 1
            frequencies[tag]["total"] += 1
            
        # Extractor 4: LLM free-tagging (if Ollama is ok)
        if ollama_ok:
            try:
                llm_tags = query_ollama_for_tags(
                    config.ollama_endpoint, config.model, page.title, page.raw_body
                )
                for tag in llm_tags:
                    frequencies[tag]["llm"] += 1
                    frequencies[tag]["total"] += 1
            except Exception as e:
                # Log warning and keep going
                sys.stdout.write(f"  [LLM Warning] Failed to query Ollama: {e}\n")
                sys.stdout.flush()
                
    # 5. Format and write the markdown table
    sorted_frequencies = sorted(
        frequencies.items(),
        key=lambda item: item[1]["total"],
        reverse=True
    )
    
    report_path = harvest_dir / "tags_frequency.md"
    
    lines = []
    lines.append("# Tag Vocabulary Harvest Report")
    lines.append("")
    lines.append(f"- **Total Drafts Processed**: {total_docs}")
    lines.append(f"- **Total Unique Tag Candidates**: {len(sorted_frequencies)}")
    lines.append(f"- **Ollama LLM Extractor (model: {config.model})**: {'Enabled' if ollama_ok else 'Disabled/Skipped'}")
    lines.append("")
    lines.append("## Frequency Table")
    lines.append("")
    lines.append("Review the candidates below to build your initial `tags.yaml` approved tags list.")
    lines.append("")
    lines.append("| Rank | Tag Candidate | Total Freq | Human Tags | Headings/Title | TF-IDF | LLM Suggested |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    
    for rank, (tag, counts) in enumerate(sorted_frequencies, 1):
        total = counts["total"]
        human = counts["human"]
        headings = counts["headings"]
        tfidf = counts["tfidf"]
        llm = counts["llm"]
        lines.append(f"| {rank} | `{tag}` | {total} | {human} | {headings} | {tfidf} | {llm} |")
        
    report_path.write_text("\n".join(lines), encoding="utf-8")
    
    sys.stdout.write(f"\nHarvest completed! Report written to: {report_path}\n")
    sys.stdout.flush()
    
    return dict(frequencies)
