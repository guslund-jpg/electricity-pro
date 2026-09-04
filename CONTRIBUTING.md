# Contributing

Thank you for your interest in contributing to Electricity Pro!

We welcome bug reports, feature requests, documentation improvements, and pull requests.

## Development Workflow

1. Fork the repository.
2. Create a dedicated branch:
   - `feature/<name>`
   - `fix/<name>`
   - `docs/<name>`
3. Make focused changes.
4. Ensure all tests and CI checks pass.
5. Open a Pull Request.

## Commit Messages

Use conventional commit messages where appropriate.

Examples:

```text
feat: add Nord Pool source adapter
fix: correct monetary sensor metadata
docs: explain clean installation
test: improve coordinator coverage
refactor: simplify provider registration
```

## Coding Guidelines

- Keep pull requests focused on a single change.
- Add or update tests when behaviour changes.
- Update documentation when introducing user-visible functionality.
- Avoid unrelated refactoring in feature pull requests.

## Pull Requests

Before opening a Pull Request, verify that:

- [ ] Tests pass
- [ ] CI passes
- [ ] Documentation is updated (if needed)
- [ ] CHANGELOG is updated for user-visible changes

## Project Principles

Electricity Pro values:

- Clear, maintainable code
- Good test coverage
- Well-defined interfaces
- Stable public behaviour
- Small, incremental improvements

The full [Design Principles](docs/vision/DESIGN_PRINCIPLES.md) explain how these
values apply to provider boundaries, normalized measurements, analytics,
entities, unavailable data, and compatibility. Review them before proposing a
new source contract or capability.

If you're unsure about a design decision, please open an issue before
implementing large changes.
