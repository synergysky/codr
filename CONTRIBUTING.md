# Contributing to Codr

Thank you for contributing to Codr! This document outlines our coding standards and workflow.

## Core Principles

### SOLID Principles

We follow SOLID principles in all code:

- **Single Responsibility Principle (SRP)**: Each class/module should have one reason to change
- **Open/Closed Principle (OCP)**: Open for extension, closed for modification
- **Liskov Substitution Principle (LSP)**: Subtypes must be substitutable for their base types
- **Interface Segregation Principle (ISP)**: Many specific interfaces are better than one general interface
- **Dependency Inversion Principle (DIP)**: Depend on abstractions, not concretions

### Code Quality

- Write clean, readable, and well-documented code in **English**
- Follow PEP 8 style guide for Python
- Use type hints for all function signatures
- Write docstrings for all public classes and functions
- Keep functions small and focused (max ~20 lines)
- Prefer composition over inheritance
- Use dependency injection over hardcoded dependencies

## Branching Strategy

### Branch Structure

- **`main`**: Production-ready code only. Protected branch.
- **`develop`**: Integration branch for features. Protected branch.
- **`feature/*`**: Feature branches (e.g., `feature/add-webhook-validation`)
- **`hotfix/*`**: Urgent fixes for production (e.g., `hotfix/fix-auth-bug`)
- **`release/*`**: Release preparation branches (optional)

### Workflow Rules

1. **Never commit directly to `main` or `develop`**
2. **Always check current branch before starting work**:
   ```bash
   git branch --show-current
   ```
3. **Always create a feature branch from `develop`**:
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```
4. **Always run unit tests before pushing**:
   ```bash
   pytest
   ```
5. **Always create a plan before coding** (document in PR or issue)

## Development Workflow

### 0. Setup Virtual Environment (First Time)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify installation
pytest --version
```

**Always activate venv before working**:
```bash
source venv/bin/activate
```

### 1. Start New Feature

```bash
# Activate virtual environment
source venv/bin/activate

# Ensure you're on develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/descriptive-name

# Verify branch
git branch --show-current
```

### 2. Make Changes

- Write code following SOLID principles
- Add/update unit tests for all changes
- Update documentation if needed
- Keep commits small and focused

### 3. Test Before Commit

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run linting (optional but recommended)
ruff check app/
mypy app/
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: descriptive commit message"
```

**Commit message format**:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Adding/updating tests
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

### 5. Push and Create PR

```bash
git push -u origin feature/your-feature-name
```

Create a Pull Request on GitHub:
- Base: `develop`
- Title: Must follow format: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`, or `hotfix:`
- Description: Link to issue, explain what/why/how
- Request review from team

**Automated Checks:**
- ✅ Branch name validation (must be `feature/*`, `hotfix/*`, etc.)
- ✅ PR title validation (must follow commit convention)
- ✅ Linting (ruff + mypy)
- ✅ Tests with 80% coverage requirement
- ✅ Docker build validation
- 📊 Coverage report posted as PR comment

### 6. After PR Approval

```bash
# Merge via GitHub UI (squash or merge commit)
# Delete feature branch after merge
git checkout develop
git pull origin develop
git branch -d feature/your-feature-name
```

## Testing Requirements

### Unit Tests

- **All new code must have unit tests**
- Aim for >80% code coverage
- Test happy paths and edge cases
- Use mocks for external dependencies (GitHub API, Zenhub API)

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── unit/
│   ├── test_config.py
│   ├── test_github_client.py
│   └── test_webhook.py
└── integration/
    └── test_e2e.py
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_config.py

# With coverage
pytest --cov=app --cov-report=html

# Watch mode (requires pytest-watch)
ptw
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Line length: 100 characters (not 79)
- Use double quotes for strings
- Use trailing commas in multi-line structures
- Sort imports: stdlib → third-party → local

### Type Hints

Always use type hints:

```python
def process_webhook(payload: dict[str, Any]) -> WebhookResponse:
    """Process incoming webhook payload.
    
    Args:
        payload: Raw webhook payload from Zenhub
        
    Returns:
        WebhookResponse with status and results
        
    Raises:
        ValidationError: If payload is invalid
    """
    ...
```

### Docstrings

Use Google-style docstrings:

```python
class GitHubClient:
    """Client for GitHub API operations.
    
    This client handles authentication and provides methods for
    creating branches, pull requests, and dispatching events.
    
    Attributes:
        token: GitHub authentication token
        base_url: GitHub API base URL
    """
    
    def __init__(self, token: str, base_url: str = "https://api.github.com") -> None:
        """Initialize GitHub client.
        
        Args:
            token: GitHub PAT or App installation token
            base_url: GitHub API base URL (default: public GitHub)
        """
        self.token = token
        self.base_url = base_url
```

## Documentation

### Code Documentation

- All public classes, functions, and methods must have docstrings
- Complex logic should have inline comments explaining "why", not "what"
- Update README.md when adding features or changing setup

### Architecture Documentation

- Document architectural decisions in `docs/architecture/`
- Use ADR (Architecture Decision Records) format for major decisions
- Keep diagrams up to date (use Mermaid or PlantUML)

## Pull Request Guidelines

### PR Checklist

Before submitting a PR, ensure:

- [ ] Code follows SOLID principles
- [ ] All tests pass (`pytest`)
- [ ] Code coverage is maintained or improved
- [ ] Documentation is updated
- [ ] Commit messages follow convention
- [ ] No secrets or credentials in code
- [ ] Branch is up to date with `develop`

### PR Template

```markdown
## Description
Brief description of changes

## Related Issue
Closes #123

## Changes Made
- Added X feature
- Refactored Y component
- Fixed Z bug

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows SOLID principles
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Security

- **Never commit secrets, API keys, or credentials**
- Use environment variables for sensitive data
- Review dependencies for vulnerabilities regularly
- Follow principle of least privilege for tokens/permissions

## Questions?

Open an issue or reach out to maintainers.

---

**Remember**: Quality over speed. Take time to write clean, testable, maintainable code.
