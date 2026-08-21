# Opening database

`openings.tsv` is the combined source snapshot from `a.tsv` through `e.tsv` in
[`lichess-org/chess-openings`](https://github.com/lichess-org/chess-openings).
The dataset is dedicated to the public domain under CC0-1.0.
The current snapshot is pinned to commit
`4b8622759e7ae6f93f011cc6c83a3823401ab45e`.

`openings.jsonl` is the deterministic runtime artifact. Generation validates
every ECO, PGN and UCI sequence, then adds legal-EPD position identity and ply
depth. `openings.metadata.json` records counts and the artifact SHA256.

Runtime opening lookup is fully local and makes no network requests. To update:

```bash
cd backend
.venv/bin/python scripts/update_opening_database.py
.venv/bin/pytest -q tests/test_opening_book.py tests/test_opening_resolver.py
```

Pin `REVISION` deliberately, run the command with developer network access,
and review all three generated files. Application startup never runs it.
