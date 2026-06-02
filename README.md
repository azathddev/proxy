# Artifact Proxy Stack

Unified proxy stack for Docker, npm, PyPI and VS Code extensions with one web portal for federated search.

## Services and URLs

- `https://registry.<domain>`: portal UI + `/api/search`
- `https://docker.<domain>`: Harbor (Docker proxy-cache)
- `https://npm.<domain>`: Verdaccio npm registry
- `https://pypi.<domain>`: devpi index for pip/uv/poetry
- `https://openvsx.<domain>`: Open VSX API / VS Code marketplace adapter

PyPI is configured independently from portal and from other registries.

## Repository Layout

- `docker-compose.yml`: devpi, Verdaccio, Open VSX, portal
- `harbor/`: official Harbor installer + config
- `openvsx/application.yml`: Open VSX upstream and local deployment config
- `verdaccio/config.yaml`: npm uplink config
- `portal/`: FastAPI backend + static UI
- `config/examples/pip.conf` and `config/examples/uv.toml`: client config templates

## Quick Start

1. Copy environment file:
   - `cp .env.example .env`
2. Update `.env` values for your domain and passwords.
3. Start base stack:
   - `docker compose up -d`
4. Harbor:
   - Edit `harbor/harbor.yml` (`hostname`, passwords, `external_url`).
   - Run `cd harbor && ./install.sh`.
   - Run `docker compose up -d` in `harbor/` (override file adds Traefik + shared network wiring).

## Harbor proxy-cache bootstrap

The stack was bootstrapped with:

- Docker Hub endpoint:
  - `POST /api/v2.0/registries` with `type: docker-hub`
- Proxy cache project:
  - `POST /api/v2.0/projects` with `project_name: dockerhub`, `registry_id: <endpoint id>`

Quick verification:

- `curl -u admin:<password> http://localhost:8088/api/v2.0/projects/dockerhub`

Use pull format:

- `docker pull docker.<domain>/dockerhub/library/nginx:latest`

## Caching Behavior (all services)

- Docker (Harbor): pull-through cache in proxy project `dockerhub`; first pull fetches from Docker Hub, next pulls are served locally.
- npm (Verdaccio): uplink cache enabled (`cache: true`, `maxage: 12h`) with persistent storage in `verdaccio_storage`.
- PyPI (devpi): on-demand mirror via `root/pypi` and persistent cache in `devpi_data`.
- VS Code extensions (Open VSX): upstream mode with local storage directory `/home/openvsx/data/storage`; downloaded extension artifacts are kept on disk in `openvsx_data`.

Note: cache persistence relies on Docker volumes (`devpi_data`, `verdaccio_storage`, `openvsx_data`, Harbor data volume).

## Client Configuration

### PyPI (independent URL)

Use only `PYPI_INDEX_URL` and `PYPI_TRUSTED_HOST`.

```bash
pip config set global.index-url "${PYPI_INDEX_URL}"
pip config set global.trusted-host "${PYPI_TRUSTED_HOST}"
export UV_INDEX_URL="${PYPI_INDEX_URL}"
```

Template files:

- `config/examples/pip.conf`
- `config/examples/uv.toml`

### npm

```bash
npm config set registry "https://npm.<domain>/"
```

### VS Code marketplace (Open VSX)

Add to `settings.json`:

```json
{
  "extensions.gallery.serviceUrl": "https://openvsx.<domain>/vscode/gallery",
  "extensions.gallery.itemUrl": "https://openvsx.<domain>/vscode/item",
  "extensions.gallery.extensionUrlTemplate": "https://openvsx.<domain>/vscode/gallery/{publisher}/{name}/latest"
}
```

## Smoke Tests

- PyPI pull-through:
  - `docker run --rm --network artifact_proxy_internal python:3.12-slim sh -lc "pip install --index-url http://devpi:3141/root/pypi/+simple/ --trusted-host devpi requests==2.32.3"`
- npm pull-through:
  - `docker run --rm --network artifact_proxy_internal node:20-alpine sh -lc "npm view lodash version --registry http://verdaccio:4873"`
- Open VSX search API:
  - `docker run --rm --network artifact_proxy_internal curlimages/curl:8.8.0 -s "http://openvsx:8080/api/-/search?query=python&size=1"`
- Portal health:
  - `docker run --rm --network artifact_proxy_internal curlimages/curl:8.8.0 -s "http://artifact-portal:8000/api/health"`
- Harbor API ping:
  - `curl http://localhost:8088/api/v2.0/ping`
- Harbor pull-through cache warm-up:
  - `docker pull localhost:8088/dockerhub/library/alpine:3.20`

