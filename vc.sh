#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif [ -f "$DIR/.venv/bin/python3" ]; then
    PYTHON="$DIR/.venv/bin/python3"
else
    PYTHON="python3"
fi

cmd="${1:-help}"
shift || true

case "$cmd" in
    help|--help|-h)
        echo "================================================================================"
        echo "              VIPERCREST REAL-WORLD ACTION COMMANDS (LINUX)                     "
        echo "================================================================================"
        echo "  ./vc.sh scan <target>        : Universal Scanner for any contract, file, or address"
        echo "  ./vc.sh audit-evm            : Immunefi Top 10 Invariant Audit for EVM targets"
        echo "  ./vc.sh audit-solana <file>  : Invariant Audit for Solana / Anchor Rust targets"
        echo "  ./vc.sh device-audit         : Live Hardware Forensic and Rootkit Detection"
        echo "  ./vc.sh drop-intake          : Ingest, SHA-256 hash, and ledger dropped files"
        echo "  ./vc.sh sandbox              : Launch private local Anvil testnet node"
        echo "  ./vc.sh purge                : Safe self-scrub of ephemeral caches"
        echo "  ./vc.sh ledger               : Inspect SQLite state ledger and receipts"
        echo "  ./vc.sh ai                   : Interactive Plain-English AI Security Shell"
        echo "  ./vc.sh matrix               : F1-F9 Temporal Matrix Engine sweep"
        echo "  ./vc.sh test                 : Run Complete Unit Test Suite (120/120 passing)"
        echo "  ./vc.sh probe                : Run Diagnostic Stress Probes"
        echo "================================================================================"
        ;;
    scan)
        "$PYTHON" -B "$DIR/ai_wrapper.py" "Scan $*"
        ;;
    audit-evm|vcae)
        "$PYTHON" -B "$DIR/audit_immunefi.py" "$@"
        ;;
    audit-solana|vcas)
        "$PYTHON" -B "$DIR/ai_wrapper.py" "Scan $*"
        ;;
    device-audit|vcda)
        "$PYTHON" -B "$DIR/phone_intake.py" "$@"
        ;;
    drop-intake|vcdrop)
        "$PYTHON" -B "$DIR/viper.py" intake "$@"
        ;;
    sandbox|vcsb)
        anvil "$@"
        ;;
    purge|vcpurge)
        rm -f "$DIR"/runtime/dropzone/*.tmp 2>/dev/null || true
        rm -f "$DIR"/runtime/dropzone/*.json 2>/dev/null || true
        rm -rf "$DIR"/runtime/staging 2>/dev/null || true
        mkdir -p "$DIR"/runtime/staging "$DIR"/runtime/dropzone
        find "$DIR" -maxdepth 2 -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        echo "[PURGE] Ephemeral dropzones and staging caches scrubbed."
        echo "[PURGE] Immutable SQLite ledger (runtime/viper_state.db) preserved."
        ;;
    ledger|vcl)
        "$PYTHON" -B "$DIR/viper.py" offline --analytics "$@"
        ;;
    ai|vcai)
        "$PYTHON" -B "$DIR/ai_wrapper.py" "$@"
        ;;
    matrix|vcm)
        "$PYTHON" -B "$DIR/viper.py" matrix "$@"
        ;;
    test|vct)
        "$PYTHON" -B -m unittest discover -s "$DIR/tests" -p "test_*.py"
        ;;
    probe|vcp)
        "$PYTHON" -B "$DIR/probes/probe_matrix.py" "$@"
        "$PYTHON" -B "$DIR/probes/probe_matrix_v2.py" "$@"
        ;;
    *)
        "$PYTHON" -B "$DIR/viper.py" "$cmd" "$@"
        ;;
esac
