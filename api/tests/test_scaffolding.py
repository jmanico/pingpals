"""Structural smoke checks for the monorepo scaffolding (REQ-FND-001).

These assert the layout/manifest invariants of issue 001 rather than runtime behaviour:
required module roots and sub-packages exist (AC-01), no `TO BE DECIDED` infrastructure SDK is a
committed API dependency (AC-02), and the secret/artifact ignore rules are present (AC-03).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC = REPO_ROOT / "api" / "src" / "pingpals_api"

# Logical ARCHITECTURE.md components that MUST have a source home (AC-01).
ARCH_SUBPACKAGES = [
    "auth",
    "scheduler",
    "delivery",
    "outreach",
    "integrations",
    "privacy",
    "persistence",
    "audit",
]

# Substrings of libraries that would resolve a `TO BE DECIDED` choice (AC-02 / anti-patterns):
# concrete DB drivers, queue/broker clients, KMS vendor SDKs, cloud SDKs.
FORBIDDEN_DEP_MARKERS = [
    "psycopg", "asyncpg", "sqlalchemy", "pg8000",          # DB drivers
    "boto3", "botocore", "google-cloud", "azure-",          # cloud / cloud-KMS SDKs
    "kombu", "celery", "pika", "redis", "kafka", "confluent",  # queue/broker clients
    "hvac",                                                  # Vault SDK (KMS vendor coupling)
]


def test_two_module_roots_with_manifests() -> None:
    assert (REPO_ROOT / "api" / "pyproject.toml").is_file()
    assert (REPO_ROOT / "web" / "package.json").is_file()


def test_arch_subpackages_present() -> None:
    for pkg in ARCH_SUBPACKAGES:
        assert (API_SRC / pkg / "__init__.py").is_file(), f"missing API sub-package: {pkg}"


def test_root_tooling_files_present() -> None:
    assert (REPO_ROOT / ".editorconfig").is_file()
    assert (REPO_ROOT / ".gitignore").is_file()


def test_no_to_be_decided_infra_dependency_committed() -> None:
    manifest = tomllib.loads((REPO_ROOT / "api" / "pyproject.toml").read_text())
    deps = [d.lower() for d in manifest["project"].get("dependencies", [])]
    for dep in deps:
        for marker in FORBIDDEN_DEP_MARKERS:
            assert marker not in dep, f"forbidden infra dependency committed: {dep!r}"


def test_gitignore_excludes_secret_and_artifact_patterns() -> None:
    ignore = (REPO_ROOT / ".gitignore").read_text()
    for pattern in [".env", "*.pem", "*.key", "node_modules/", ".venv/"]:
        assert pattern in ignore, f".gitignore missing pattern: {pattern}"


def test_spa_module_has_no_server_only_subpackages() -> None:
    """Client/server separation (AC-04): the SPA must not contain server-only packages."""
    web_src = REPO_ROOT / "web" / "src"
    if not web_src.exists():
        return
    forbidden = {"persistence", "auth", "audit", "scheduler", "delivery", "integrations"}
    present = {p.name for p in web_src.iterdir() if p.is_dir()}
    assert not (present & forbidden), f"SPA contains server-only package(s): {present & forbidden}"
