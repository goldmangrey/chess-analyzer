# Opening database

`openings.tsv` is generated from the `a.tsv` through `e.tsv` files in
[`lichess-org/chess-openings`](https://github.com/lichess-org/chess-openings).
The dataset is dedicated to the public domain under CC0-1.0.
The current snapshot is pinned to commit
`4b8622759e7ae6f93f011cc6c83a3823401ab45e`.

Runtime opening recognition is fully local and makes no network requests.
To refresh the vendored snapshot deliberately, pin `REVISION` in
`scripts/update_opening_database.py`, run the script, and review the generated
diff and opening resolver tests.
