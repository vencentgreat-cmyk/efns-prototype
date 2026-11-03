# Branch relationship audit — 2026-11-03

Audit basis: fetched remote refs on 2026-11-03. This report does not verify the
deployed application.

## Relationship summary

| Comparison | Merge-base | Ahead / behind | Result |
|---|---|---:|---|
| `history-view-fix-20261102` (`5922230`) → `codex-handoff-20261103` (`ccbbabf`) | `5922230` | handoff is 1 ahead, 0 behind | The handoff branch is the history-fix source plus one documentation commit. |
| R3 `delivery-candidate-r3-20261030` (`a7b0abb`) → history fix (`5922230`) | `a7b0abb` | history fix is 1 ahead, 0 behind | The history fix is exactly one code-fix commit after R3. |
| `origin/main` (`46af180`) ↔ history fix (`5922230`) | `123a644` | main is 1 ahead; history fix is 35 ahead | Neither tip contains the other. |

`ccbbabf` contains the Change history fix. Its first parent is `5922230`, whose
commit message is `Fix bounded per-record change history display`. That fix adds
`app/services/revision_history.py`, changes `app/pages/21_Record_History.py`, and
adds the bounded `get_record_revisions_for(..., limit=50)` repository path.

The only commit added by the handoff branch is `ccbbabf Add Codex continuation
handoff for November 3`; it adds `docs/CODEX_HANDOFF_20261103.md`. It does not
change runtime code.

## Ancestry diagram

```text
123a644  common ancestor of main and the release line
├─ ... 34 further release-line commits ... ─ a7b0abb (R3)
│                                      └─ 5922230 (Change history fix)
│                                         └─ ccbbabf (handoff Markdown only)
└─ 46af180 (origin/main merge commit)
```

Commands used: `git merge-base`, `git rev-list --left-right --count`, `git log`,
and `git diff --name-status`. No branch was merged or rebased.
