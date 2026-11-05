"""SAE J2534 Windows Registry Installer & Export Tool (register_j2534.py).

Registers the Sovereign Pass-Thru device for VCI Serial 989510052355
so that standard OEM diagnostic suites (Techstream, ODIS, GDS2, FDRS, FORScan, ISTA)
automatically recognize your SmartLink VCI as an approved J2534 tool.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VCI_SERIAL = "989510052355"
DEVICE_NAME = f"ViperCrest_SmartLink_{VCI_SERIAL}"
DLL_PATH = str(PROJECT_ROOT / "os_builder" / "j2534_bridge.dll").replace("/", "\\")


def generate_reg_content() -> str:
    """Generates standard Windows .reg file content for both 32-bit and 64-bit systems."""
    return f"""Windows Registry Editor Version 5.00

; ====================================================================
; ViperCrest Sovereign SAE J2534-1 / J2534-2 Registry Registration
; Target VCI Serial: {VCI_SERIAL}
; ====================================================================

; 64-bit Native Registration
[HKEY_LOCAL_MACHINE\\SOFTWARE\\PassThruSupport.04.04\\{DEVICE_NAME}]
"Name"="ViperCrest SmartLink J2534 ({VCI_SERIAL})"
"Vendor"="ViperCrest Sovereign Engine"
"ConfigURL"="https://github.com/nowlinc46-droid/VIPER_CREST_2.0"
"FunctionLibrary"="{DLL_PATH}"
"CAN"=dword:00000001
"ISO15765"=dword:00000001
"ISO9141"=dword:00000001
"ISO14230"=dword:00000001
"CAN_FD"=dword:00000001
"SCI_A_ENGINE"=dword:00000000
"SCI_A_TRANS"=dword:00000000
"SCI_B_ENGINE"=dword:00000000
"SCI_B_TRANS"=dword:00000000

; 32-bit WOW6432Node Registration (for 32-bit OEM software: Techstream, ODIS, GDS2)
[HKEY_LOCAL_MACHINE\\SOFTWARE\\WOW6432Node\\PassThruSupport.04.04\\{DEVICE_NAME}]
"Name"="ViperCrest SmartLink J2534 ({VCI_SERIAL})"
"Vendor"="ViperCrest Sovereign Engine"
"ConfigURL"="https://github.com/nowlinc46-droid/VIPER_CREST_2.0"
"FunctionLibrary"="{DLL_PATH}"
"CAN"=dword:00000001
"ISO15765"=dword:00000001
"ISO9141"=dword:00000001
"ISO14230"=dword:00000001
"CAN_FD"=dword:00000001
"SCI_A_ENGINE"=dword:00000000
"SCI_A_TRANS"=dword:00000000
"SCI_B_ENGINE"=dword:00000000
"SCI_B_TRANS"=dword:00000000
"""


def export_reg_file(out_path: Optional[Path] = None) -> Path:
    p = out_path or (PROJECT_ROOT / "runtime" / f"register_j2534_{VCI_SERIAL}.reg")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(generate_reg_content(), encoding="utf-8")
    return p


def main():
    parser = argparse.ArgumentParser(description="J2534 PassThru Registry Tool")
    parser.add_argument("--export", action="store_true", help="Generate .reg file for installation")
    args = parser.parse_args()

    reg_file = export_reg_file()
    print("=" * 72)
    print("   VIPERCREST SAE J2534 PASSTHRU REGISTRATION")
    print("=" * 72)
    print(f"  Target VCI Serial : {VCI_SERIAL}")
    print(f"  Device Name       : ViperCrest SmartLink J2534 ({VCI_SERIAL})")
    print(f"  Protocol Support  : CAN, CAN-FD, ISO15765, ISO9141, ISO14230")
    print(f"  Registry File     : {reg_file}")
    print("=" * 72)
    print("  To activate, simply merge the .reg file or run as Administrator.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
