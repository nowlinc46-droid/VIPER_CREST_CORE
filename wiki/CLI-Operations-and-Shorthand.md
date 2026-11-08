# ⌨️ CLI Operations & Shorthand Quick Reference

ViperCrest provides clean, single-command CLI launchers for rapid evaluation, security audits, and operations.

---

## 🏛️ Essential Operational Commands

| Shorthand | Script | Target Script | Description |
| :--- | :--- | :--- | :--- |
| `vct` | `vct.cmd` | `tests/` | Runs the complete unit and integration regression test suite. |
| `vcp` | `vcp.cmd` | `probes/` | Runs historical prototype boundary probes (31/31 passing). |
| `vcs` | `vcs.cmd` | `session_router.py` | Inspects and audits the SQLite WAL ledger and 5-file session bundles. |
| `vcdisc` | `vcdisc.cmd`| `discovery_cli.py` | Launches interactive real-time Open Ontological Discovery REPL. |
| `vcstem` | `vcstem.cmd`| `the_stem/cli.py` | Displays live status of The Stem physical robotics governor. |
| `vcstv` | `vcstv.cmd` | `the_stem/verify_stem.py` | Runs standalone self-verification test suite for The Stem (5/5 PASS). |
| `vcaaos` | `vcaaos.cmd`| `os_builder/aaos_cli.py` | Launches Android Automotive OS (AAOS) VHAL safety monitor. |
| `vchf` | `vchf.cmd` | `run_hustleforge_100.py` | Executes the complete HustleForge 100-scenario curriculum. |

---

## 💻 Interactive AI Shell (`vc-ai`)

Launch the interactive operator terminal under strict epistemic authority boundaries:

```powershell
vc-ai.cmd
# or
python ai_wrapper.py
```

### Supported Shell Directives:
* `status`: Displays active database runs, ledger health, and memory footprint.
* `matrix <target.json>`: Evaluates a target JSON fixture across the full F1–F9 matrix.
* `hydrate <seed_text>`: Hydrates unstructured seed text into the 81-coordinate matrix.
* `discovery`: Opens the scale-invariant open discovery REPL.
* `verify`: Executes the 8-pillar asset diligence runner in real time.
* `exit`: Terminates session cleanly.
