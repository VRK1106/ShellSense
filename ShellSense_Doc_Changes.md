# ShellSense Documentation: Changes Made

Version 1.3.0 · October 2026

## 1. Claims corrected

| # | Section | Change |
|---|---|---|
| 1 | USPs (item 2), Conclusion, Target Audience | "Zero-knowledge encrypted vault" renamed "client-side encrypted vault". Target Audience now says "Client-side credential encryption, on-device decryption on the desktop". |
| 2 | 5.8 Vault spec table, 9.2 Security table | The "Zero knowledge" row became "Master password". It now says: never stored; on the desktop it never leaves the device and decryption is on-device; web-dashboard vault operations use the `/api/vault` endpoints over HTTPS. |
| 3 | 13 Competitive Analysis | Raycast column is now "macOS, Windows" (it left beta on Windows on August 21, 2026). PowerToys live currency changed from "No" to "Community extension". The "AI code agent" row became "Embedded AI" (ShellSense: Groq LLM agent, config editing; Raycast: AI Chat (Pro)). |
| 4 | 12 Market Gap | Added "partly paid (Raycast, now also on Windows)" to the list of tools. "None combine" became "To the author's knowledge, none combine". |
| 5 | 7 Tech Stack, 8.2 AI Code Agent | Model ID `qwen/qwen3.8-27b` replaced with `qwen/qwen3-32b` in both places (the Qwen ID on Groq's model list). |
| 6 | 5.2 Calculations | Removed "sandboxed". `eval()` is now described as "restricted to a whitelisted math namespace". |
| 7 | 2 Problem Statement | Removed the unsourced "23 times per hour" and "1.6 billion active users". Rewritten to say Windows has no built-in launcher comparable to Spotlight and that PowerToys, Flow Launcher and Raycast each leave gaps. |
| 8 | 12 Market table heading | Now "Global Addressable Market (rough estimates, sources to be added)". |
| 9 | 17 Impact | Heading is now "Estimated Time Savings per Task". "Conservative estimate" became "Estimate (author's assumptions, not measured)". |
| 10 | 8.2 | "Safety" label changed to "Generation controls" (temperature and token limits are not safety measures). |
| 11 | 11 Version History | "v3.1 (current)" became "v3.1 (current; app release v1.3.0)". |

## 2. Planned hardening added

| # | Section | Change |
|---|---|---|
| 12 | 8.1 Confidence gating | Now reads: below 35% confidence queries currently run with a warning log. Planned hardening: reject low-confidence matches and require confirmation for POWER_OFF, RESTART and PROCESS_KILL. |
| 13 | USPs (item 4) | AI code agent now notes a file allow-list, diff preview and rollback are on the roadmap. |
| 14 | 16 Roadmap (near-term) | Added three items: safer command execution (reject low-confidence matches, confirm destructive intents); AI code agent hardening (file allow-list, diff preview, rollback); fully client-side vault operations in the web dashboard so the master password never reaches the server. |

Items 12 to 14 describe work not yet built. Implement them or remove them before submitting.

## 3. Left unchanged and unverified

- Raycast Pro "$8/mo", plus the Raycast encrypted vault and cloud sync cells
- "Under 100 ms" hotkey claim
- "No API cost" claim for the on-device brain
- Market-size figures (only relabeled as estimates)
- Whether the master password is sent to the server in the web dashboard (check against your code)
