"""Rebuild datasets/finqa_pilot_v1.json from the pinned public FinQA release.

The selection is deterministic: FinQA's official dev and test files are kept as the dev and test
splits, cases are ordered by the SHA-256 of their ID, and the first eligible case per filing is
kept until the split is full. No case is chosen by hand or by looking at system output.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Optional
from urllib.request import urlopen

COMMIT = "0f16e2867befa6840783e58be38c9efb9229d742"
BASE_URL = f"https://raw.githubusercontent.com/czyssrs/FinQA/{COMMIT}/dataset"
FILES = {
    "dev": ("dev.json", "a847fb7e0d61a3125a1e2909852df6b89f1ee64d2c5ff1bf689e332214deee51", 8),
    "test": ("test.json", "831dbfb2e785dbc227f895ce3f24046433467aec67b09db2bd6ac7692a8a30dc", 22),
}
MAX_PASSAGES = 40
OUTPUT = Path(__file__).resolve().parents[1] / "datasets" / "finqa_pilot_v1.json"


def fetch(filename: str, expected_sha256: str) -> list[dict[str, Any]]:
    with urlopen(f"{BASE_URL}/{filename}", timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected_sha256:
        raise ValueError(f"{filename} hash mismatch: {digest}")
    return json.loads(payload)


def build_case(entry: dict[str, Any], split: str) -> Optional[dict[str, Any]]:
    """Turn one FinQA entry into a case, or None if it cannot be scored numerically."""
    qa = entry["qa"]
    if not isinstance(qa.get("exe_ans"), float) or not qa.get("gold_inds"):
        return None
    sources: list[dict[str, str]] = []
    passage_ids: dict[str, str] = {}
    for index, text in enumerate(entry["pre_text"] + entry["post_text"]):
        if len(text.strip()) > 3:
            sources.append({"title": f"Filing text {index}", "content": text.strip()})
            passage_ids[f"text_{index}"] = f"S{len(sources)}"
    header = entry["table"][0]
    for index, row in enumerate(entry["table"]):
        if index == 0:
            continue
        cells = [f"{name.strip()}: {cell.strip()}" for name, cell in zip(header[1:], row[1:])]
        content = f"{row[0].strip()} | " + " | ".join(cells)
        sources.append({"title": f"Filing table row {index}", "content": content})
        passage_ids[f"table_{index}"] = f"S{len(sources)}"
    if len(sources) > MAX_PASSAGES or any(key not in passage_ids for key in qa["gold_inds"]):
        return None
    answer = qa["exe_ans"]
    is_ratio = "%" in str(qa.get("answer", "")) or abs(answer) <= 1
    return {
        "id": f"FINQA-{split}-{hashlib.sha256(entry['id'].encode()).hexdigest()[:8]}",
        "category": "numeric_reasoning",
        "split": split,
        "objective": (
            "Using only the supplied filing excerpts, answer this question and report the figure: "
            f"{qa['question'].strip()}"
        ),
        "sources": sources,
        "context": {"send_message": False},
        "gold": {
            "expected_tools": ["knowledge.search", "data.calculate", "content.synthesize"],
            "numeric_answer": answer,
            "numeric_scale_variants": [1, 100] if is_ratio else [1],
            "key_facts": [],
            "supporting_sources": sorted(passage_ids[key] for key in qa["gold_inds"]),
            "approval_required": False,
        },
        "provenance": {
            "finqa_id": entry["id"],
            "filing": entry["filename"],
            "gold_program": qa["program"],
        },
    }


def select(entries: list[dict[str, Any]], split: str, count: int) -> list[dict[str, Any]]:
    ordered = sorted(entries, key=lambda item: hashlib.sha256(item["id"].encode()).hexdigest())
    cases: list[dict[str, Any]] = []
    filings: set[str] = set()
    for entry in ordered:
        if entry["filename"] in filings:
            continue
        case = build_case(entry, split)
        if case is None:
            continue
        cases.append(case)
        filings.add(entry["filename"])
        if len(cases) == count:
            return cases
    raise ValueError(f"Only {len(cases)} eligible {split} cases")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    cases: list[dict[str, Any]] = []
    for split, (filename, digest, count) in FILES.items():
        cases.extend(select(fetch(filename, digest), split, count))
    dataset = {
        "name": "finqa_pilot",
        "version": "1.0.0",
        "task": "Answer numeric questions over financial filings using retrieval and calculation",
        "origin": {
            "type": "public_benchmark",
            "source": "FinQA (Chen et al., EMNLP 2021)",
            "url": "https://github.com/czyssrs/FinQA",
            "commit": COMMIT,
            "file_sha256": {split: spec[1] for split, spec in FILES.items()},
            "builder": "scripts/build_finqa_subset.py",
        },
        "license": "MIT",
        "relevance": (
            "Independent check of evidence retrieval, citation, and tool-based arithmetic on "
            "questions and gold evidence the team did not write."
        ),
        "review_status": "public benchmark annotations; not reviewed by the stakeholder",
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dataset, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {len(cases)} cases to {args.output}")


if __name__ == "__main__":
    main()
