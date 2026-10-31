# 🧭 Session Router & Intent Management

The **Session Router** (`session_router.py`) orchestrates execution isolation, state persistence, replay defense, and intent lifecycle tracking within ViperCrest.

---

## 📂 Session Isolation & Storage

Every execution creates an immutable session container under `runtime/sessions/`:
```
runtime/sessions/session_<TIMESTAMP>_<TAG>-<HASH>/
├── manifest.json       # Execution parameters, timestamps, status code
├── input_fixture.json  # Raw input snapshot
├── evaluation.json     # Matrix score output & F1-F9 validation results
└── signature.sig       # Cryptographic signature over manifest
```

---

## 🛡️ Intent Model & Error Handling

ViperCrest encapsulates operations within explicit `Intent` objects. Any violation of execution boundaries raises a typed `IntentError`:

- **Path Escape Rejections**: Attempts to resolve paths containing parent directory traversal (`..`) or absolute external paths are blocked.
- **Fixture Resolution Guard**: Fixtures are resolved strictly from the bundled `fixtures/` directory or active runtime staging.
- **Replay Protection**: Identical payloads evaluated under strict replay prevention rules verify previous hashes before state updates.

---

## 🔗 Related Notes
- [[System Architecture]]
- [[Agnostic 9x9 Matrix Protocol]]
- [[SQLite Database Schema & WAL]]
