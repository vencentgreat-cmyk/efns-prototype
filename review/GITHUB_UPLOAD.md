# GitHub publication instructions and preparation boundary

Follow-up authorization: the user selected the existing public repository
`https://github.com/vencentgreat-cmyk/efns-prototype` and authorized publication
of exactly this clean file list on `codex/offline-review-20261028`, without
inheriting old history or changing other branches. The workflow now triggers
on pushes to this branch only, in addition to its existing review triggers.
Actual publication/CI results are reported separately with commit and run IDs;
the original preparation record below is retained as historical context.

The clean expanded upload directory is `efns-independent-review`, next to this
preparation area's working `source` directory. Do not upload the original EFNS
working tree or its `.git`. Do not upload the preparation directory, logs,
archives or its private test output. All commands below are for the clean
review directory after the user confirms a suitable private repository URL.

1. In GitHub create an **empty private repository**, without generated README,
   license or `.gitignore`. Confirm its URL and authorize the external AI tool
   for this repository only. Do not grant access to company data or secrets.
2. From the clean directory, run `python scripts/check_review_package.py` and
   inspect `review/SUBMISSION_FILES.txt` and `review/SHARING_AUDIT.md`.
3. Only after URL confirmation, initialize an independent history and stage
   exactly the reviewed manifest, not a blanket `git add .`:

```powershell
Set-Location 'C:\Users\Egg Farmers\Desktop\efns\efns-prototype\.local\github_review_20261028\efns-independent-review'
git init -b codex/offline-review-20261028
git --literal-pathspecs add --pathspec-from-file=review/SUBMISSION_FILES.txt
git diff --cached --check
git diff --cached --name-only
git status --short
# Inspect the complete staged diff and confirm the target repository is private.
git commit -m "Prepare isolated EFNS offline review candidate"
$repoUrl = 'REPLACE_WITH_CONFIRMED_PRIVATE_REPOSITORY_URL'
git remote add origin $repoUrl
git remote -v
git push -u origin codex/offline-review-20261028
```

At the original preparation snapshot these init/stage/commit/push commands had
not been run. Subsequent authorized review publication uses only the independent
directory. The original repository does not have a branch created, commits rewritten or
remote changed. A new private remote avoids publishing old history. An already
populated destination needs a separate review before combining histories;
do not force-push or use `--allow-unrelated-histories` as a shortcut.

After upload, select branch `codex/offline-review-20261028` in the external tool;
read README/REVIEW_GUIDE, run the offline tests, then produce file-level findings.
No CI run has occurred locally. The included workflow is a prepared Linux
verification path, not evidence of successful GitHub Actions execution.
