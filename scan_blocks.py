import json
import urllib.request
import sys

RPC_URL = "http://127.0.0.1:8545"


def call_rpc(method, params=None):
    if params is None:
        params = []

    data = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params,
    }).encode()

    req = urllib.request.Request(
        RPC_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        response = json.loads(resp.read().decode())

    if "error" in response:
        raise RuntimeError(response["error"])

    return response["result"]


def main():
    try:
        latest_hex = call_rpc("eth_blockNumber")
    except Exception as exc:
        print(f"[!] Could not connect to RPC at {RPC_URL}: {exc}", file=sys.stderr)
        print("[!] Ensure anvil or your EVM node is running (e.g. 'anvil').", file=sys.stderr)
        return 1

    latest = int(latest_hex, 16)
    print(f"[*] Latest Block Height: {latest}")

    start_block = max(0, latest - 100)
    print(
        f"[*] Scanning blocks {start_block} to {latest} "
        "for gaps and parent-hash discontinuities...\n"
    )

    prev_block = None
    issues = []

    for num in range(start_block, latest + 1):
        blk = call_rpc(
            "eth_getBlockByNumber",
            [hex(num), False],
        )

        if not blk:
            print(f"[!] MISSING BLOCK: #{num}")
            issues.append(num)
            prev_block = None
            continue

        current_hash = blk["hash"]
        parent_hash = blk["parentHash"]

        if prev_block is not None:
            expected_parent = prev_block["hash"]

            if parent_hash != expected_parent:
                print(f"[!] CONTINUITY BREAK at block #{num}")
                print(f"    Expected Parent: {expected_parent}")
                print(f"    Actual Parent:   {parent_hash}")
                print(f"    Current Hash:    {current_hash}")
                issues.append(num)

        prev_block = blk

    if not issues:
        print(
            "\n[+] SCAN COMPLETE: No missing blocks or "
            "parent-hash discontinuities found."
        )
    else:
        print(f"\n[-] Total issues found: {len(issues)}")
        print(f"[-] Affected heights: {issues}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
