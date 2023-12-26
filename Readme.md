# Conflict resolver

A POS of a conflict resolving utility for back-porting code. Based on the ``git diff`` utility.

## Requirements

- [Docker]()

## Installation

Build Docker image

```bash
docker build . -t conflict-resolver
```

Run conflict resolver in docker

```bash
docker run --rm -v "$PWD:/app" conflict-resolver python app.py %path_to_before% %path_to_after% %path_to_target%
```

