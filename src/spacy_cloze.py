"""
spaCy-based cloze (fill-in-the-blank) selector for Spanish.
Provides tokenization, POS-based candidate selection, and hint generation.

This module is designed to assist or replace AI-based cloze selection
for improved precision and speed, while remaining compatible with the
current UI which expects word-index positions based on `text.split()`.

It respects spaCy-only configuration in the provided `config` dict under
`spacy_options`, independent of AI-specific focus areas. Options:
- spacy_options.pos: list of POS tags to consider (e.g., ["NOUN","VERB","ADJ","ADV"]).
- spacy_options.max_blanks: max blanks per sentence (int).
- spacy_options.exclude_stop: whether to exclude stopwords (bool).
- spacy_options.hint_lemma: whether to include lemma in hint (bool).
- spacy_options.prefer_entities: bias selection toward named entities/PROPN (bool).
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import re

_NLP_CACHE: Dict[str, object] = {}


def _strip_punct(word: str) -> str:
    return word.strip('.,!?;:"()[]{}¡¿…“”’\'`、·—-')


def _pos_zh(pos: str) -> str:
    mapping = {
        'NOUN': '名词',
        'PROPN': '专有名词',
        'VERB': '动词',
        'AUX': '助动词',
        'ADJ': '形容词',
        'ADV': '副词',
        'PRON': '代词',
        'DET': '限定词',
        'ADP': '介词',
        'CCONJ': '并列连词',
        'SCONJ': '从属连词',
        'NUM': '数词',
        'PART': '小品词',
        'INTJ': '感叹词',
        'SYM': '符号',
    }
    return mapping.get(pos, pos)


def ensure_nlp(language: str) -> Optional[object]:
    """Lazily load spaCy model for a language. Currently supports Spanish.

    Returns the spaCy Language object or None if unavailable.
    """
    lang_key = language.lower()
    if lang_key in _NLP_CACHE:
        return _NLP_CACHE[lang_key]

    try:
        import spacy  # type: ignore
        if lang_key in ("spanish", "es", "español"):
            try:
                nlp = spacy.load("es_core_news_md")
            except Exception:
                # Fallback to small model if md not available
                nlp = spacy.load("es_core_news_sm")
        else:
            return None
        _NLP_CACHE[lang_key] = nlp
        return nlp
    except Exception:
        return None


def _align_spacy_tokens_to_split_words(text: str, doc) -> Dict[int, int]:
    """Map spaCy token indices -> indices in `text.split()` array.

    The UI uses `text.split()`; we align alpha tokens to those indices.
    If a spaCy token cannot be aligned reliably, it is skipped.
    """
    words = text.split()
    norm_words = [_strip_punct(w).lower() for w in words]
    mapping: Dict[int, int] = {}

    i = 0
    for j, tok in enumerate(doc):
        if not tok.text or not tok.text.strip():
            continue
        # focus on alphabetic tokens for cloze
        if not tok.is_alpha:
            continue
        tnorm = tok.text.lower()
        k = i
        found = None
        while k < len(norm_words):
            if norm_words[k] == tnorm:
                found = k
                break
            k += 1
        if found is not None:
            mapping[j] = found
            i = found + 1
    return mapping


def _candidate_mask(pos: str, allowed_pos: Optional[List[str]], focus_areas: Optional[List[str]]) -> bool:
    """Decide whether a token POS is eligible.

    - If `allowed_pos` provided (spaCy local mode), use it directly.
    - Else, fallback to mapping from AI `focus_areas`.
    """
    if allowed_pos:
        return pos in set(allowed_pos)
    fa = {x.lower() for x in (focus_areas or [])}
    if not fa:
        return pos in {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}
    rules = []
    if "nouns" in fa:
        rules.append(pos in {"NOUN", "PROPN"})
    if "verbs" in fa:
        rules.append(pos in {"VERB", "AUX"})
    if "adjectives" in fa:
        rules.append(pos == "ADJ")
    if "adverbs" in fa:
        rules.append(pos == "ADV")
    return any(rules) or pos in {"NOUN", "PROPN", "VERB", "ADJ", "ADV"}


def _difficulty_by_len(s: str) -> str:
    L = len(s)
    if L <= 4:
        return "easy"
    if L <= 7:
        return "medium"
    return "hard"


def suggest_candidates_for_ai(text: str, config: Dict) -> List[Dict]:
    """Return candidate blanks (position/word) to assist AI prompting.

    Keeps compatibility with UI by using word indices from `text.split()`.
    """
    language = (config.get("language") or "").strip() or "Spanish"
    nlp = ensure_nlp(language)
    if not nlp:
        return []
    doc = nlp(text)
    align = _align_spacy_tokens_to_split_words(text, doc)

    focus_areas = config.get("focus_areas", [])
    spacy_opts = (config or {}).get("spacy_options", {}) or {}
    allowed_pos = spacy_opts.get("pos")
    exclude_stop = bool(spacy_opts.get("exclude_stop", True))
    prefer_entities = bool(spacy_opts.get("prefer_entities", True))
    max_blanks = int(spacy_opts.get("max_blanks", 2))
    words = text.split()

    # Collect candidate tokens
    candidates: List[Tuple[int, object]] = []  # (word_index, token)
    for tidx, tok in enumerate(doc):
        if tidx not in align:
            continue
        if not tok.is_alpha:
            continue
        if exclude_stop and tok.is_stop:
            continue
        if not _candidate_mask(tok.pos_, allowed_pos, focus_areas):
            continue
        widx = align[tidx]
        base = _strip_punct(words[widx])
        if not base:
            continue
        candidates.append((widx, tok))

    # Deduplicate by word index, prefer longer tokens
    by_index: Dict[int, object] = {}
    for widx, tok in sorted(candidates, key=lambda x: (-len(x[1].text), x[0])):
        by_index.setdefault(widx, tok)

    # Determine count: prefer spaCy max_blanks if set
    if max_blanks and max_blanks > 0:
        target = max_blanks
    else:
        density = int(config.get("blank_density", 25))
        target = max(1, int(len(words) * density / 100))
        target = max(1, min(2, target))

    # Ranking: prefer entities/PROPN if requested, then longer tokens
    def _rank(item):
        _, tok = item
        ent_bonus = 1 if prefer_entities and (tok.ent_iob_ != 'O' or tok.pos_ == 'PROPN') else 0
        return (ent_bonus, len(tok.text))

    selection = sorted(by_index.items(), key=_rank, reverse=True)[:target]

    result: List[Dict] = []
    for widx, tok in selection:
        answer = _strip_punct(words[widx])
        if not answer:
            continue
        result.append({
            "position": widx,
            "word": answer,
            "pos": tok.pos_,
            "lemma": tok.lemma_,
            "cn_pos": _pos_zh(tok.pos_),
        })
    return result


def select_blanks_spacy(text: str, config: Dict) -> List[Dict]:
    """Select blanks purely via spaCy, producing UI-compatible entries.

    Returns a list of dicts with keys: position, answer, hint, difficulty.
    """
    language = (config.get("language") or "").strip() or "Spanish"
    nlp = ensure_nlp(language)
    if not nlp:
        return []

    doc = nlp(text)
    align = _align_spacy_tokens_to_split_words(text, doc)
    words = text.split()
    focus_areas = config.get("focus_areas", [])
    spacy_opts = (config or {}).get("spacy_options", {}) or {}
    allowed_pos = spacy_opts.get("pos")
    exclude_stop = bool(spacy_opts.get("exclude_stop", True))
    hint_lemma = bool(spacy_opts.get("hint_lemma", True))
    prefer_entities = bool(spacy_opts.get("prefer_entities", True))
    max_blanks = int(spacy_opts.get("max_blanks", 2))

    # collect candidates
    candidates: List[Tuple[int, object]] = []
    for tidx, tok in enumerate(doc):
        if tidx not in align:
            continue
        if not tok.is_alpha:
            continue
        if exclude_stop and tok.is_stop:
            continue
        if not _candidate_mask(tok.pos_, allowed_pos, focus_areas):
            continue
        widx = align[tidx]
        base = _strip_punct(words[widx])
        if not base:
            continue
        candidates.append((widx, tok))

    # Fallback to any non-stop alpha tokens if none matched focus areas
    if not candidates:
        for tidx, tok in enumerate(doc):
            if tidx not in align:
                continue
            if not tok.is_alpha:
                continue
            if exclude_stop and tok.is_stop:
                continue
            widx = align[tidx]
            base = _strip_punct(words[widx])
            if not base:
                continue
            candidates.append((widx, tok))

    if not candidates:
        return []

    # Dedup by word index; prefer entities and longer tokens
    by_index: Dict[int, object] = {}
    def _rankcand(c):
        widx, tok = c
        ent_bonus = 1 if prefer_entities and (tok.ent_iob_ != 'O' or tok.pos_ == 'PROPN') else 0
        return (ent_bonus, len(tok.text), -widx)
    for widx, tok in sorted(candidates, key=_rankcand, reverse=True):
        by_index.setdefault(widx, tok)

    if max_blanks and max_blanks > 0:
        target = max_blanks
    else:
        density = int(config.get("blank_density", 25))
        target = max(1, int(len(words) * density / 100))
        target = max(1, min(2, target))

    # Final selection with same ranking as above
    def _rankfinal(item):
        _, tok = item
        ent_bonus = 1 if prefer_entities and (tok.ent_iob_ != 'O' or tok.pos_ == 'PROPN') else 0
        return (ent_bonus, len(tok.text))
    selection = sorted(by_index.items(), key=_rankfinal, reverse=True)[:target]

    blanks: List[Dict] = []
    for widx, tok in selection:
        answer = _strip_punct(words[widx])
        if not answer:
            continue
        hint_parts = [
            _pos_zh(tok.pos_),
        ]
        # Add lemma hint if enabled
        if hint_lemma:
            lem = tok.lemma_.lower()
            if lem and lem != answer.lower():
                hint_parts.append(f"词根：{lem}")
        if answer:
            hint_parts.append(f"首字母：{answer[0].lower()}")

        blanks.append({
            "position": widx,
            "answer": answer,
            "hint": "，".join(hint_parts),
            "difficulty": _difficulty_by_len(answer),
        })

    return blanks
