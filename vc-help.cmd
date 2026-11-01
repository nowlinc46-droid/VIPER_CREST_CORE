@echo off
echo ======================================================================
echo  ViperCrest Shorthand Command Reference
echo ======================================================================
echo  vc        : Main ViperCrest CLI wrapper (e.g. vc matrix, vc online, vc offline)
echo  vcm       : Matrix evaluation (shorthand for 'vipercrest matrix')
echo  vco       : Controlled online HTTPS intake (shorthand for 'vipercrest online')
echo  vcoff     : Offline management/analytics (shorthand for 'vipercrest offline')
echo  vcb       : Universal 9x9 Agnostic Syntax Bridge (bridge_9x9_syntax.py)
echo  vcf       : Foundry Simulation Bridge (bridge_foundry.py)
echo  vci       : Phone and USB dropzone intake pipeline (phone_intake.py)
echo  vcread    : Air-Gapped Reader (RAW -> Normalized Matrix) (reader_engine.py)
echo  vca       : Immunefi Top 10 Invariant Security Audit (audit_immunefi.py)
echo  vct       : Run test suite (unittest)
echo  vcp       : Execute diagnostic probes (probe_matrix.py / probe_matrix_v2.py)
echo  vcs       : Quick status / offline database analytics check
echo  vcr       : Run offline verification script (run_offline.ps1)
echo  vch       : Display this help reference
echo.
echo  Long-form aliases (vc-matrix, vc-online, vc-offline, vc-bridge,
echo  vc-foundry, vc-intake, vc-reader, vc-audit, vc-test, vc-probe,
echo  vc-status, vc-run, vc-help) are also supported.
echo ======================================================================
exit /b 0
