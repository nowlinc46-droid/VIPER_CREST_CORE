"""
Universal Agnostic F1-F9 Intake & Positioning Bridge for ViperCrest.

Enforces the core Human OS / A Logical Engine invariant:
  "One fixed neutral F1-F9 engine. Application context, mapping, data,
   interface, and output may vary; the engine does not." (neutral_intent = True)

- Accepts ANY file or directory regardless of extension, language, or domain
  (all programming languages, documents, configs, custom extensions, extensionless
  files, and opaque/binary artifacts).
- Never drops unknown file types: unreadable/binary files are hashed, positioned via
  deterministic SHA-256 fallback, and flagged for F7 Discovery.
- Positions every record across the Canonical F1-F9 Logical Engine spine AND extracts
  universal 9-stage structural/syntax signals when readable text is present.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VIPER_ROOT = Path("C:/ViperCrest")
FIXTURES_DIR = VIPER_ROOT / "fixtures"
PYTHON_EXE = VIPER_ROOT / ".venv" / "Scripts" / "python.exe"

# Optional descriptive classification only — NEVER used to filter or reject files.
KNOWN_SYNTAX_FAMILIES: dict[str, dict[str, str]] = {
    ".py":   {"id": "M1_Python",     "name": "Python",     "paradigm": "dynamic_duck_typed"},
    ".js":   {"id": "M2_JavaScript", "name": "JavaScript", "paradigm": "dynamic_event_driven"},
    ".mjs":  {"id": "M2_JavaScript", "name": "JavaScript", "paradigm": "dynamic_event_driven"},
    ".cjs":  {"id": "M2_JavaScript", "name": "JavaScript", "paradigm": "dynamic_event_driven"},
    ".ts":   {"id": "M3_TypeScript", "name": "TypeScript", "paradigm": "static_structural"},
    ".tsx":  {"id": "M3_TypeScript", "name": "TypeScript", "paradigm": "static_structural"},
    ".java": {"id": "M4_Java",       "name": "Java",       "paradigm": "static_nominal_jvm"},
    ".cs":   {"id": "M5_CSharp",     "name": "C#",         "paradigm": "static_nominal_clr"},
    ".cpp":  {"id": "M6_Cpp",        "name": "C++",        "paradigm": "static_raii_zero_cost"},
    ".cc":   {"id": "M6_Cpp",        "name": "C++",        "paradigm": "static_raii_zero_cost"},
    ".cxx":  {"id": "M6_Cpp",        "name": "C++",        "paradigm": "static_raii_zero_cost"},
    ".hpp":  {"id": "M6_Cpp",        "name": "C++",        "paradigm": "static_raii_zero_cost"},
    ".c":    {"id": "M7_C",          "name": "C",          "paradigm": "static_procedural_systems"},
    ".h":    {"id": "M7_C",          "name": "C/C++ Header","paradigm": "static_procedural_systems"},
    ".go":   {"id": "M8_Go",         "name": "Go",         "paradigm": "static_structural_csp"},
    ".rs":   {"id": "M9_Rust",       "name": "Rust",       "paradigm": "static_affine_ownership"},
    ".sol":  {"id": "M_Solidity",    "name": "Solidity",   "paradigm": "static_evm_contract"},
    ".ps1":  {"id": "M_PowerShell",  "name": "PowerShell", "paradigm": "object_pipeline_shell"},
    ".bat":  {"id": "M_Batch",       "name": "Batch",      "paradigm": "command_shell"},
    ".sh":   {"id": "M_Shell",       "name": "POSIX Shell","paradigm": "command_shell"},
    ".sql":  {"id": "M_SQL",         "name": "SQL",        "paradigm": "declarative_relational"},
    ".md":   {"id": "M_Markdown",    "name": "Markdown",   "paradigm": "declarative_specification"},
    ".json": {"id": "M_JSON",        "name": "JSON",       "paradigm": "structured_state"},
    ".jsonl":{"id": "M_JSONL",       "name": "JSONL",      "paradigm": "structured_stream"},
    ".yaml": {"id": "M_YAML",        "name": "YAML",       "paradigm": "declarative_config"},
    ".yml":  {"id": "M_YAML",        "name": "YAML",       "paradigm": "declarative_config"},
    ".toml": {"id": "M_TOML",        "name": "TOML",       "paradigm": "declarative_config"},
    ".xml":  {"id": "M_XML",         "name": "XML",        "paradigm": "structured_markup"},
    ".html": {"id": "M_HTML",        "name": "HTML",       "paradigm": "declarative_markup"},
    ".css":  {"id": "M_CSS",         "name": "CSS",        "paradigm": "declarative_style"},
}

# Canonical Neutral F1-F9 Positions (Human OS / A Logical Engine)
CANONICAL_F1_F9: dict[str, str] = {
    "F1": "Identity / Intake (What entered?)",
    "F2": "Chronology / Change (When did it exist or change?)",
    "F3": "Support / Evidence (What supports it?)",
    "F4": "Direct Artifacts (What direct material exists?)",
    "F5": "Governing / Reference (What governs or constrains it?)",
    "F6": "Correspondence / Interaction (What was communicated or exchanged?)",
    "F7": "Discovery / Unknown (What is unknown or still required?)",
    "F8": "Opposing / Transition (What competes, contradicts, or can transition?)",
    "F9": "Ledger / Result (What bounded state was reached?)",
}

# Universal structural & syntax patterns (language-agnostic + cross-paradigm)
STAGE_PATTERNS: dict[str, re.Pattern[str]] = {
    "F1_identity_intake_primitives": re.compile(
        r"\b(id|identity|name|title|subject|import|from|include|using|package|use|pragma|const|let|var|uint256|int32_t|string|bool|u64|i32)\b",
        re.IGNORECASE,
    ),
    "F2_chronology_scoping_control": re.compile(
        r"\b(date|time|timestamp|version|created|updated|before|after|if|else|elif|switch|match|case|for|while|loop|break|continue|public|private|internal|external)\b",
        re.IGNORECASE,
    ),
    "F3_evidence_functions_closures": re.compile(
        r"\b(evidence|fact|proof|metric|test|verify|def|function|fn|func|lambda|yield|return|modifier|delegate|Action|Func)\b|=>",
        re.IGNORECASE,
    ),
    "F4_artifacts_data_modeling": re.compile(
        r"\b(artifact|document|file|exhibit|record|schema|class|struct|interface|trait|enum|type|union|contract|library|impl)\b",
        re.IGNORECASE,
    ),
    "F5_governing_rules_error_arch": re.compile(
        r"\b(rule|policy|invariant|constraint|standard|authority|must|shall|try|catch|except|finally|raise|throw|panic|recover|Result|Option|require|revert|err)\b",
        re.IGNORECASE,
    ),
    "F6_interaction_collections": re.compile(
        r"\b(message|request|response|event|channel|emit|route|list|dict|set|Map|Set|Vec|HashMap|List|Dictionary|vector|mapping|slice|range)\b",
        re.IGNORECASE,
    ),
    "F7_discovery_memory_concurrency": re.compile(
        r"\b(unknown|missing|unresolved|todo|fixme|question|discovery|async|await|thread|go|chan|select|Mutex|RwLock|Arc|Box|unique_ptr|shared_ptr|malloc|free|storage|memory|calldata|unsafe)\b",
        re.IGNORECASE,
    ),
    "F8_opposing_transition_testing": re.compile(
        r"\b(versus|conflict|contradiction|diff|compare|transition|alternative|assert|assertEq|expect|describe|it|pytest|JUnit|Fact|cmake|cargo|forge)\b",
        re.IGNORECASE,
    ),
}

STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "into", "are", "was",
    "were", "have", "has", "not", "but", "you", "your", "file", "data",
}
TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_-]{2,}")


def try_decode_text(raw_bytes: bytes) -> tuple[str, bool]:
    """Attempt UTF-8 decoding without rejecting binary/opaque payloads."""
    if not raw_bytes:
        return "", False
    if b"\x00" in raw_bytes[:8192]:
        return "", False
    try:
        return raw_bytes.decode("utf-8"), True
    except UnicodeDecodeError:
        return raw_bytes.decode("utf-8", errors="replace"), True


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    tokens = {
        m.group(0)
        for m in TOKEN_RE.finditer(text.lower())
        if m.group(0) not in STOPWORDS
    }
    return sorted(tokens)


def collect_target_files(target: Path, max_files: int = 100) -> list[Path]:
    """Agnostic file collector: accepts ANY file extension or extensionless file."""
    if target.is_file():
        return [target]
    excluded = {".git", ".venv", "venv", "node_modules", "__pycache__", "out", "cache"}
    collected: list[Path] = []
    for p in sorted(target.rglob("*")):
        if any(part in excluded for part in p.parts):
            continue
        if p.is_file():
            collected.append(p)
            if len(collected) >= max_files:
                break
    return collected


def build_agnostic_observations(
    files: list[Path], root_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw_records: list[dict[str, Any]] = []
    global_token_counts: Counter[str] = Counter()

    for file_path in files:
        raw_bytes = file_path.read_bytes()
        sha256_hex = hashlib.sha256(raw_bytes).hexdigest()
        text, text_available = try_decode_text(raw_bytes)
        tokens = tokenize(f"{file_path.stem} {text}" if text_available else file_path.stem)
        global_token_counts.update(tokens)
        raw_records.append(
            {
                "file_path": file_path,
                "raw_bytes": raw_bytes,
                "sha256": sha256_hex,
                "text": text,
                "text_available": text_available,
                "tokens": tokens,
            }
        )

    # Dataset-wide token anchor grouping across F1..F9 (from A_LOGICAL_ENGINE)
    top_anchors = [tok for tok, _ in global_token_counts.most_common(72)]
    f_groups: dict[int, set[str]] = {i: set() for i in range(1, 10)}
    for idx, tok in enumerate(top_anchors):
        f_groups[(idx % 9) + 1].add(tok)

    observations: list[dict[str, Any]] = []
    occupied_positions: set[str] = set()

    for rec in raw_records:
        file_path = rec["file_path"]
        ext = file_path.suffix.lower()
        lang_info = KNOWN_SYNTAX_FAMILIES.get(
            ext,
            {
                "id": f"M_Agnostic_{ext.lstrip('.') or 'extensionless'}",
                "name": f"Agnostic ({ext or 'extensionless'})",
                "paradigm": "domain_and_syntax_agnostic",
            },
        )

        # Score F1..F9 position from dataset relationships, with deterministic SHA-256 fallback
        scores = {
            node: sum(1 for tk in rec["tokens"] if tk in f_groups[node])
            for node in range(1, 10)
        }
        best_node = max(range(1, 10), key=lambda n: (scores[n], -n))
        if scores[best_node] == 0:
            seed = int(rec["sha256"][:8], 16)
            f_node = (seed % 9) + 1
            basis = "neutral_deterministic_sha256_fallback"
        else:
            f_node = best_node
            basis = "dataset_relationship_match"

        f_pos = f"F{f_node}"
        occupied_positions.add(f_pos)

        stage_counts: dict[str, int] = {}
        for stage_key, pattern in STAGE_PATTERNS.items():
            stage_counts[stage_key] = (
                len(pattern.findall(rec["text"])) if rec["text_available"] else 0
            )

        rel_path = (
            file_path.relative_to(root_path).as_posix()
            if file_path != root_path
            else file_path.name
        )

        discovery_flags: list[str] = []
        if not rec["text_available"]:
            discovery_flags.append("opaque_or_binary_payload_requires_external_inspector")
        if sum(stage_counts.values()) == 0:
            discovery_flags.append("no_structural_keywords_matched_positioned_by_hash")

        observations.append(
            {
                "id": f"{f_pos}::{lang_info['id']}::{rel_path}",
                "baseline": {
                    "engine": "HUMAN_OS_LOGICAL_ENGINE_F1_F9",
                    "neutral_intent": True,
                    "canonical_position": f_pos,
                    "canonical_role": CANONICAL_F1_F9[f_pos],
                    "syntax_family": lang_info["name"],
                    "status": "neutral_intake_reference",
                },
                "candidate": {
                    "engine": "HUMAN_OS_LOGICAL_ENGINE_F1_F9",
                    "neutral_intent": True,
                    "canonical_position": f_pos,
                    "canonical_role": CANONICAL_F1_F9[f_pos],
                    "positioning_basis": basis,
                    "relationship_score": scores[best_node],
                    "syntax_family": lang_info["name"],
                    "paradigm": lang_info["paradigm"],
                    "text_available": rec["text_available"],
                    "token_count": len(rec["tokens"]),
                    "F1_F8_stage_signals": stage_counts,
                    "F7_discovery_flags": discovery_flags,
                    "F9_production_provenance": {
                        "relative_path": rel_path,
                        "extension": ext or "<extensionless>",
                        "sha256": rec["sha256"],
                        "bytes": len(rec["raw_bytes"]),
                        "lines": len(rec["text"].splitlines()) if rec["text_available"] else 0,
                    },
                    "status": (
                        "DISCOVERY_REQUIRED" if discovery_flags else "BOUNDED_OBSERVATION"
                    ),
                },
            }
        )

    empty_positions = [f"F{i}" for i in range(1, 10) if f"F{i}" not in occupied_positions]
    summary = {
        "engine": "HUMAN_OS_LOGICAL_ENGINE_F1_F9",
        "neutral_intent": True,
        "files_ingested": len(observations),
        "positions_occupied": sorted(occupied_positions),
        "empty_positions": empty_positions,
        "discovery_status": "DISCOVERY_REQUIRED" if empty_positions else "DISCOVERY_BOUNDED",
    }
    return observations, summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Universal Agnostic F1-F9 Intake & Positioning Bridge for ViperCrest"
    )
    parser.add_argument(
        "--target",
        "--input",
        dest="target",
        required=True,
        type=Path,
        help="Path to ANY file or directory (any language, document, data, or binary payload)",
    )
    parser.add_argument(
        "--name",
        default="agnostic_f1_f9_intake.json",
        help="Output fixture filename in C:\\ViperCrest\\fixtures\\",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=100,
        help="Maximum files to ingest from a directory",
    )
    parser.add_argument(
        "--transport",
        choices=("direct", "http"),
        default="direct",
        help="ViperCrest F1-F9 matrix transport mode",
    )
    args = parser.parse_args()

    target = args.target.resolve()
    if not target.exists():
        print(f"[AGNOSTIC-F1-F9] ERROR: Target path does not exist: {target}", file=sys.stderr)
        sys.exit(2)

    files = collect_target_files(target, max_files=args.max_files)
    if not files:
        print(f"[AGNOSTIC-F1-F9] ERROR: No files found in: {target}", file=sys.stderr)
        sys.exit(2)

    observations, summary = build_agnostic_observations(files, target)
    fixture_name = args.name if args.name.endswith(".json") else f"{args.name}.json"
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path = FIXTURES_DIR / fixture_name

    fixture_payload = {
        "observations": observations,
    }
    fixture_path.write_text(json.dumps(fixture_payload, indent=2), encoding="utf-8")

    families = sorted({obs["candidate"]["syntax_family"] for obs in observations})
    print(f"[AGNOSTIC-F1-F9] Neutral Intent: {summary['neutral_intent']}")
    print(f"[AGNOSTIC-F1-F9] Ingested {len(observations)} file(s) from: {target}")
    print(f"[AGNOSTIC-F1-F9] Occupied F1-F9 Positions: {', '.join(summary['positions_occupied'])}")
    print(f"[AGNOSTIC-F1-F9] Empty Positions (Discovery): {', '.join(summary['empty_positions']) or 'None (9/9 occupied)'}")
    print(f"[AGNOSTIC-F1-F9] Detected Families: {', '.join(families)}")
    print(f"[AGNOSTIC-F1-F9] Wrote fixture: {fixture_path}")

    cmd = [
        str(PYTHON_EXE),
        "-B",
        str(VIPER_ROOT / "viper.py"),
        "matrix",
        "--target",
        str(fixture_path),
        "--transport",
        args.transport,
    ]
    if args.transport == "http":
        cmd.extend(["--http-port", "0"])

    print(f"[AGNOSTIC-F1-F9] Dispatching to ViperCrest F1-F9 Matrix: {' '.join(cmd)}")
    res = subprocess.run(cmd, text=True)
    sys.exit(res.returncode)


if __name__ == "__main__":
    main()
