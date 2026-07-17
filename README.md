# Peddler

Peddles your CV, door to door, one job application form at a time.

[![CI](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml/badge.svg)](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- PyPI badge added by /publish once the first version ships -->

## Visuals

![Peddler logo](docs/logo.png)

## Prerequisites

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- Claude CLI

## Installation

```bash
uv sync
```

## Usage

From Claude CLI:

```
/apply <jd.md> <url>
```

## Contributing

Pull requests welcome. Please make sure `ruff check`, `radon cc -n B`, and `pytest --cov` all pass before
opening a PR.

## License

MIT
