# Project working rules

- Keep all work for this project, including code, documentation, data, and generated artifacts, inside `GoT-war/`.
- Commit all project changes directly to `main`.
- Do not create new branches.
- Do not push commits; the user handles pushing.
- Keep raw runs, caches, downloaded weights, expanded benchmark inputs and preview PNGs local and ignored. Publish code/configurations, manuscript, SVG/PDF figures, concise results and the curated reproduction archive.
- Before committing, run `python3 scripts/check_release.py` from `GoT-war/` against the staged files. The release limits are 360 files, 9.5 MiB total and 2 MiB per file. The separately requested complete conference draft adds ten file slots and 0.5 MiB beyond the prior 350-file/9-MiB release, preserving all original results and manuscripts; see `docs/REPOSITORY_STORAGE.md` for this and earlier bounded allowances. Do not bypass these limits or force-add ignored campaign artifacts; update the documented release policy if research requirements change.
