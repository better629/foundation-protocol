# Operations

## Quality gates

Run this before release:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py' -q
python3 -m compileall -q src tests
python3 scripts/validate_specs.py
```

## Documentation workflow

This project uses **MkDocs + Material + mkdocstrings**:

- Markdown pages for architecture and guides
- Automatic API reference from Python source
- Static site output for easy hosting (GitHub Pages, Netlify, internal portal)

Install docs dependencies:

```bash
python3 -m pip install -e ".[docs]"
```

Preview locally:

```bash
bash scripts/serve_docs.sh
```

Build static site:

```bash
bash scripts/build_docs.sh
```

The generated site is written to `site/`.

## CI recommendation

Use the following checks in CI:

1. `scripts/run_tests.sh`
2. `python3 scripts/validate_specs.py`
3. `scripts/build_docs.sh` (strict mode enabled in `mkdocs.yml`)
