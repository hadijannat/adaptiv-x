# Contributing to Adaptiv-X

Thank you for your interest in contributing to Adaptiv-X!

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/your-feature`
4. Make your changes
5. Run tests: `poetry run pytest`
6. Submit a pull request

## Development Setup

```bash
# Python services
cd services/adaptiv-monitor
poetry install
poetry run pytest

# Run linting
poetry run ruff check src/
poetry run mypy src/
```

## Code Style

- Python: Follow Ruff defaults (PEP 8 based)
- Use type hints for all function signatures
- Write docstrings for public APIs
- Keep functions focused and testable

## Commit Messages

Use conventional commits:
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Test additions/changes

## Pull Request Process

1. Update documentation for any API changes
2. Add tests for new functionality
3. Ensure CI passes
4. Request review from maintainers

## Reporting Issues

Please include:
- Clear description
- Steps to reproduce
- Expected vs actual behavior
- Environment details

## Code of Conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
