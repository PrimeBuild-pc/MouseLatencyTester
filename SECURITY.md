# Security policy

## Supported versions

| Version | Supported |
|---|---|
| 3.0.x | ✅ |
| < 3.0 | ❌ (the single-file dashboards in `legacy/` are archival) |

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Use GitHub's private reporting instead:
[**Report a vulnerability**](https://github.com/PrimeBuild-pc/MouseLatencyTester/security/advisories/new)

That opens a private advisory visible only to the maintainers. You will get a
first response within 7 days. If a fix is needed, it ships in the next release
and you get credit in the advisory unless you ask otherwise.

## What is in scope

This is a desktop measurement tool. The parts worth reporting are:

- **Arbitrary code execution** from opening a crafted archive (`.db`), a CSV,
  or a `settings.json`.
- **Path traversal** in the CSV / chart / backup export paths.
- **SQL injection** in the archive layer.
- Anything in the **release installer** — tampering, unexpected privilege
  escalation, or writes outside the install directory.
- Supply-chain problems in the pinned dependencies.

## What is out of scope

- The app reads **global mouse events** via `pynput`. This is the measurement
  itself, not a flaw — `t₁` is the moment the OS reports the click. It is
  documented, it is local-only, and nothing is transmitted anywhere.
- The app opens a **serial port** and speaks a plain-text protocol to a device
  you physically attached. A hostile device on that port can send garbage; the
  parser treats every unknown line as log text, but this is not a trust
  boundary we can meaningfully defend.
- **The installer is not code-signed.** Windows SmartScreen will warn on first
  run. Verify the SHA-256 published with the release instead. Reports that
  "the binary is unsigned" are known, not vulnerabilities.
- Anything requiring an attacker who already has local code execution as your
  user.

## Privacy

Latency Tester has **no telemetry, no network code, and no auto-update**. It
never sends anything anywhere. All measurements stay in a local SQLite file
under your Documents folder.
