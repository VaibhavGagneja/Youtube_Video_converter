# Contributing Guide

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- `make` (optional)

### Getting Started

```bash
# 1. Clone the repo
git clone https://github.com/vaibhavgagneja/Youtube_Video_converter.git
cd Youtube_Video_converter

# 2. Set up environment
cp .env.example .env
# Edit .env with your values

# 3. Start services
make up

# 4. Verify
curl http://localhost:8080/health
```

## Development Workflow

### Branch Strategy

```
main ← staging ← feature/your-feature
```

1. Create a feature branch from `staging`
2. Make changes, write tests
3. Open a PR → CI runs automatically (lint, test, build)
4. Merge to `staging` → auto-deploys to staging environment
5. Promote `staging` → `main` → auto-deploys to production

### Making Changes

```bash
# Run linter before committing
make lint

# Run tests
make test

# Build images locally
make build
```

### Adding a New Service

1. Create `src/your-service/` with `Dockerfile`, `requirements.txt`, source code
2. Add a test directory `src/your-service/tests/`
3. Add the service to `docker-compose.yml`
4. Add Helm templates in `helm/video-converter/templates/`
5. Add values in `helm/video-converter/values.yaml`
6. Add the service to the CI matrix in `.github/workflows/ci.yml`

## Code Standards

- **Linter:** flake8, max line length 120
- **Tests:** pytest with mocks for external dependencies
- **Dockerfiles:** Multi-stage builds, non-root user
- **Commits:** Conventional commits (`feat:`, `fix:`, `docs:`, `chore:`)
