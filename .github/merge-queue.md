# Merge Queue — enable via Settings, not a YAML file

Enable GitHub Merge Queue at: Settings → Rules/Branches → develop →
"Require merge queue". There's no config file in the repo; this is just a note.

Why it's needed: multiple PRs being green at the same time does NOT guarantee it's safe
to merge them together. The merge queue lines them up, rebases each onto the state that
already includes the earlier PRs, re-runs CI, then merges sequentially. This is what
turns "parallel" into "safe integration".

Suggested config for develop:
  - Require merge queue: ON
  - Build concurrency: 3-5 (PRs tested concurrently in the queue)
  - Only merge if checks pass: ON
  - Merge method: Squash
