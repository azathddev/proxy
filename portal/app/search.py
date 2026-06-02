import asyncio
import os
import re
from typing import Any

import httpx


HARBOR_API_URL = os.getenv("HARBOR_API_URL", "http://harbor-core/api/v2.0").rstrip("/")
VERDACCIO_URL = os.getenv("VERDACCIO_URL", "http://verdaccio:4873").rstrip("/")
DEVPI_URL = os.getenv("DEVPI_URL", "http://devpi:3141").rstrip("/")
OPENVSX_URL = os.getenv("OPENVSX_URL", "http://openvsx:8080").rstrip("/")

PUBLIC_DOCKER_REGISTRY = os.getenv("PUBLIC_DOCKER_REGISTRY", "https://docker.azathd.ru").rstrip("/")
HARBOR_PROXY_PROJECT = os.getenv("HARBOR_PROXY_PROJECT", "dockerhub")
PUBLIC_NPM_REGISTRY = os.getenv("PUBLIC_NPM_REGISTRY", "https://npm.azathd.ru").rstrip("/")
PUBLIC_PYPI_INDEX_URL = os.getenv(
    "PUBLIC_PYPI_INDEX_URL", "https://pypi.azathd.ru/root/pypi/+simple/"
).rstrip("/")
PUBLIC_PYPI_TRUSTED_HOST = os.getenv("PUBLIC_PYPI_TRUSTED_HOST", "pypi.azathd.ru")
PUBLIC_OPENVSX_GALLERY = os.getenv(
    "PUBLIC_OPENVSX_GALLERY", "https://openvsx.azathd.ru/vscode/gallery"
).rstrip("/")


def _safe(text: str) -> str:
    return text.strip() if text else ""


async def search_harbor(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    response = await client.get(f"{HARBOR_API_URL}/search", params={"q": query})
    response.raise_for_status()
    payload = response.json()
    repos = payload.get("repository", [])
    results: list[dict[str, Any]] = []
    for repo in repos:
        project = _safe(repo.get("project_name") or HARBOR_PROXY_PROJECT)
        repo_name = _safe(repo.get("repository_name") or "")
        if not repo_name:
            continue
        image = repo_name.split("/", 1)[1] if "/" in repo_name else repo_name
        results.append(
            {
                "type": "docker",
                "name": repo_name,
                "url": f"{PUBLIC_DOCKER_REGISTRY}/harbor/projects/{project}/repositories/{repo_name}",
                "pull": f"docker pull {PUBLIC_DOCKER_REGISTRY}/{project}/{image}:latest",
            }
        )
    return results


async def search_verdaccio(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"{VERDACCIO_URL}/-/v1/search",
        params={"text": query, "size": 20, "from": 0},
    )
    response.raise_for_status()
    payload = response.json()
    objects = payload.get("objects", [])
    results: list[dict[str, Any]] = []
    for obj in objects:
        pkg = obj.get("package") or {}
        name = _safe(pkg.get("name") or "")
        if not name:
            continue
        version = _safe(pkg.get("version") or "")
        results.append(
            {
                "type": "npm",
                "name": name,
                "version": version,
                "url": f"{PUBLIC_NPM_REGISTRY}/{name}",
                "install": f"npm i {name}",
            }
        )
    return results


async def search_devpi(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    response = await client.get(f"{DEVPI_URL}/+search", params={"query": f"name:{query}*"})
    response.raise_for_status()
    html = response.text
    # devpi renders results as links to /<user>/<index>/<package>
    packages = sorted(set(re.findall(r'href="/[^"]*/([^"/?#]+)"', html)))
    results: list[dict[str, Any]] = []
    for pkg in packages[:20]:
        results.append(
            {
                "type": "pypi",
                "name": pkg,
                "url": f"{PUBLIC_PYPI_INDEX_URL}/{pkg}",
                "install": f"pip install {pkg} --index-url {PUBLIC_PYPI_INDEX_URL}/ --trusted-host {PUBLIC_PYPI_TRUSTED_HOST}",
            }
        )
    return results


async def search_openvsx(client: httpx.AsyncClient, query: str) -> list[dict[str, Any]]:
    response = await client.get(
        f"{OPENVSX_URL}/api/-/search",
        params={"query": query, "size": 20, "offset": 0},
    )
    response.raise_for_status()
    payload = response.json()
    extensions = payload.get("extensions", [])
    results: list[dict[str, Any]] = []
    for ext in extensions:
        namespace = _safe(ext.get("namespace") or "")
        name = _safe(ext.get("name") or "")
        if not namespace or not name:
            continue
        display = _safe(ext.get("displayName") or f"{namespace}.{name}")
        version = _safe(ext.get("version") or "")
        results.append(
            {
                "type": "extension",
                "name": f"{namespace}.{name}",
                "displayName": display,
                "version": version,
                "url": ext.get("url") or f"{OPENVSX_URL}/extension/{namespace}/{name}",
                "marketplace": PUBLIC_OPENVSX_GALLERY,
            }
        )
    return results


async def aggregated_search(query: str, search_type: str) -> dict[str, Any]:
    timeout = httpx.Timeout(10.0)
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        tasks: list[tuple[str, Any]] = []
        if search_type in ("all", "docker"):
            tasks.append(("docker", search_harbor(client, query)))
        if search_type in ("all", "npm"):
            tasks.append(("npm", search_verdaccio(client, query)))
        if search_type in ("all", "pypi"):
            tasks.append(("pypi", search_devpi(client, query)))
        if search_type in ("all", "extension"):
            tasks.append(("extension", search_openvsx(client, query)))

        outcomes = await asyncio.gather(*(t[1] for t in tasks), return_exceptions=True)
        for idx, outcome in enumerate(outcomes):
            source = tasks[idx][0]
            if isinstance(outcome, Exception):
                errors.append({"source": source, "error": str(outcome)})
            else:
                results.extend(outcome)

    return {"query": query, "type": search_type, "results": results, "errors": errors}


async def health_check() -> dict[str, Any]:
    timeout = httpx.Timeout(5.0)
    checks = {
        "harbor": f"{HARBOR_API_URL}/ping",
        "verdaccio": f"{VERDACCIO_URL}/-/ping",
        "devpi": f"{DEVPI_URL}/",
        "openvsx": f"{OPENVSX_URL}/api/-/search?query=python&size=1",
    }
    status: dict[str, dict[str, Any]] = {}
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        for name, url in checks.items():
            try:
                resp = await client.get(url)
                status[name] = {"ok": resp.status_code < 500, "status_code": resp.status_code}
            except Exception as exc:
                status[name] = {"ok": False, "error": str(exc)}
    return status

