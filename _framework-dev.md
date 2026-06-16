# Framework Dev Notes

Tracks progress and context for building and improving this repo itself.

-----

## Status
`In Progress`

## What This Repo Is
A reusable Claude project template. Clone it for any new project, fill in `1. Project Management/`, paste `Cowork Instructions - Paste.md` into the Claude project instructions field.

## Current State
- [x] Initial file structure created
- [x] All 5 project management templates in place
- [x] `CLAUDE.md` with session routines and rules
- [x] `Cowork Instructions - Paste.md` for Claude project instructions field

## Backlog / Future Improvements

- [ ] Consider adding a `.github/` folder with issue/PR templates
- [ ] Explore making this a proper GitHub template repo (repo settings)
- [ ] Evaluate whether `4. Technical Reference.md` needs more scaffolding
- [ ] Consider a quick-start README explaining how to use the template

## Notes

- The `.txt` extension issue on some files was a Claude Code download quirk — source files are all `.md`
- `CLAUDE.md` serves double duty: Claude Code reads it automatically at session start, and it documents the framework for humans
- Initial session was run from mobile — no local git clone exists; commits exist only on remote
- Keep this file lean — it's a dev scratchpad, not a full project tracker

## The Two Instruction Files

The framework ships two instruction files that serve different Claude interfaces:

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root-level instructions for **Claude Code** (CLI). Loaded automatically at session start when running `claude` from the project directory. |
| `Cowork Instructions - Paste.md` | Source content for **Claude.ai Projects** ("Cowork") — paste into the Project Instructions field in the UI. |

### Cleanup Workflow
Once you've determined which Claude interface is running the project, delete the file that doesn't apply — it can always be retrieved from this framework repo.

- Running via **Claude Code (CLI)**? Delete `Cowork Instructions - Paste.md`.
- Running via **Claude.ai Project (Cowork)**? Delete `CLAUDE.md`.
- Running **both**? Keep both — they serve different sessions.

-----

## Session History

### 2026-06-11 - Initial setup
Created full file structure from uploaded templates. Added `_framework-dev.md` (this file) for meta-tracking.
