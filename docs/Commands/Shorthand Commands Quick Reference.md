# ⚡ Shorthand Commands Quick Reference

ViperCrest provides single-token shorthand commands and descriptive long-form aliases located in the root repository.

---

## 🚀 Complete Command Matrix

| Shorthand | Long-form Alias | Target Script / Operation | Typical Syntax |
| :--- | :--- | :--- | :--- |
| `vc` | `vipercrest` | Primary launcher | `vc matrix --target fixtures\example.json` |
| `vcm` | `vc-matrix` | Matrix evaluation | `vcm --target fixtures\example.json` |
| `vco` | `vc-online` | Controlled HTTPS intake | `vco --url <URL> --case-id <ID>` |
| `vcoff` | `vc-offline` | Offline analytics / management | `vcoff --analytics` |
| `vcb` | `vc-bridge` | Agnostic 9x9 Syntax Bridge | `vcb --input <FILE> --format 9x9` |
| `vcf` | `vc-foundry` | Foundry Bridge | `vcf --scenario <NAME>` |
| `vct` | `vc-test` | Test Suite Execution | `vct` |
| `vcp` | `vc-probe` | Diagnostic Probe Suite | `vcp` |
| `vcs` | `vc-status` | State Database Analytics | `vcs` |
| `vcr` | `vc-run` | Offline Execution Script | `vcr` |
| `vch` | `vc-help` | Interactive Command Reference | `vch` |

---

## 💡 Subcommand Aliases in `viper.py`

When using `vc` or `vipercrest`, subcommands also support ultra-short aliases:
- `vc m` ➔ `vc matrix`
- `vc on` ➔ `vc online`
- `vc off` ➔ `vc offline`

---

## 🔗 Related Notes
- [[CLI Launcher (vc & vipercrest)]]
- [[Universal 9x9 Syntax Bridge (vcb)]]
- [[Offline Analytics & Database (vcs)]]
