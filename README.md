# MacroForge — public product walkthrough

This public repository demonstrates how MacroForge is used without including the Windows application's source code or binaries. The current development repository is private.

**Live page:** <https://mohamed3042.github.io/macroforge-demo/>

## What is here

- A source-free product walkthrough.
- A source-free HTML representation of the visible Studio workflow.
- A concise usage flow and command-family overview.
- Measured proof from the independent Windows acceptance run.

## What is not here

- MacroForge desktop source, project files, tests, or build scripts.
- Executables, libraries, debug symbols, or macro files.
- Any new licence beyond the existing MacroForge v1.0.0 MIT grant.

The HTML, CSS, and JavaScript in this repository power only the public presentation page. They are not the MacroForge application implementation. MacroForge v1.0.0 was previously released publicly under MIT; making the current source repository private does not revoke copies or licence grants already made.

## Verified product proof

The packaged v1.0.0 Windows run passed 14/14 deterministic tests. An external UI Automation process found 11 required controls, converted 2 recorded events into 6 visible rows, triggered exactly 1 color-branch click, and read back the exact 68-character result in Windows Notepad.

## Local preview

```powershell
python -m http.server 4173
```

Then open <http://127.0.0.1:4173/>.

## Verification

```powershell
python tools\site_gate.py
python tools\site_gate.py --base-url http://127.0.0.1:4173/
```

Run the second command while the local preview server is open. The gate rejects desktop source/binary extensions, checks the visible private-source boundary, drives the interactive walkthrough at desktop and phone sizes, detects horizontal overflow and browser errors, verifies reduced-motion behavior, and refuses external network requests.

## Safety boundary

MacroForge is a local, user-space personal automation workbench. The demonstrated product has no telemetry, phone-home behavior, remote configuration, process hiding, anti-cheat bypass, or kernel driver.

Copyright © 2026 Mohamed Mahmoud. See [NOTICE.md](NOTICE.md).
