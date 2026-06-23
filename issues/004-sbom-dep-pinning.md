# Requirement: SBOM generation and integrity-verified dependency pinning

## Metadata
- **ID**: REQ-FND-004
- **Title**: Generate an SBOM and pin all dependency versions with integrity (hash) verification
- **Version**: 1.0.0
- **Status**: Approved
- **Author**: Spec decomposition (Claude)
- **Last Updated**: 2026-06-23
- **Priority**: High
- **Classification**: Security

## Requirement
- **Description**: The build MUST generate a **software bill of materials (SBOM)** for both the Flask API and the React 19 SPA, and ALL dependency versions (direct and transitive) MUST be **pinned with integrity verification** — i.e. exact versions plus cryptographic hashes recorded in lockfiles, so an installed artifact whose hash does not match is rejected. Each new dependency MUST be **minimized and vetted** (known CVEs, maintenance status, transitive footprint) before introduction. Installs in CI and in the Docker build MUST be hash-checked and MUST fail closed on any hash mismatch.
- **Rationale**: `SEC-9.3` mandates an SBOM and integrity-pinned dependencies; `SEC-9.1` mandates minimization and vetting. Pinning with hashes defends against dependency substitution and tampering in the supply chain; the SBOM is the inventory that SCA (003) and breach assessment (`PRIV-1.14`) rely on. This complements `ARCHITECTURE.md` Dependency Rule 10 ("new third-party dependencies are minimized and vetted before introduction").
- **Design**: No UI. The SBOM is a build artifact consumed by tooling and audit; no design-token or visual concern applies.

## Scope
- **Applies To**: Both
- **Components**: API dependency manifests/lockfiles (pip hashes / equivalent); SPA `package.json` + lockfile with integrity hashes; SBOM generator wired into the build (001/002/003).
- **Actors**: CI build pipeline, developers adding dependencies, auditors consuming the SBOM.
- **Data Classification**: Internal (the SBOM lists components, no personal data or secrets).

## Security Context
- **Defense Layer**: Architecture / supply-chain integrity
- **Threat(s) Addressed**: Dependency confusion / substitution (CWE-427/CWE-829), compromised or yanked package versions, unvetted transitive bloat (A06:2021 vulnerable & outdated components). STRIDE: Tampering, Spoofing of package provenance.
- **Trust Boundary**: The dependency-resolution boundary — what third-party code enters the build. A hash mismatch denies entry.
- **Zero Trust Consideration**: No package is trusted by name/version alone; its content hash MUST match the pinned value or installation fails closed. Provenance is re-verified at every install.

## Standards Alignment
- **OWASP ASVS**: V14.2 (dependency management & integrity)
- **OWASP AISVS**: n/a
- **NIST SP 800-53**: SA-12/SR-3 (supply chain protection), CM-2, RA-5
- **NIST SP 800-207**: continuous verification of build inputs
- **Regulatory**: n/a (supports `PRIV-1.14` breach-scoping via component inventory)
- **Other**: SECURITY §8, `SEC-9.1`, `SEC-9.3`, ARCH Dependency Rule 10; SBOM formats (SPDX / CycloneDX — selection `TO BE DECIDED`, keep behind the generator)

## Acceptance Criteria
1. **AC-01**: Given a build, when it completes, then an SBOM listing all API and SPA components (with versions) is produced as a retained artifact.
2. **AC-02 (verbatim `SEC-9.3`)**: Given the dependency manifests, when inspected, then every dependency version is pinned and integrity (hash) verification is configured.
3. **AC-03 (negative)**: Given an installed package whose content hash does not match the pinned hash, when install runs in CI or the Docker build, then installation fails closed and the build is blocked.
4. **AC-04 (negative)**: Given a PR that adds a dependency without a recorded hash/pin, when CI runs, then the dependency-pinning check fails the build.
5. **AC-05**: Given a newly proposed dependency, when reviewed, then a vetting record (CVE check, maintenance status, transitive footprint) exists per `SEC-9.1` before it is merged.

## Failure Behavior
- **On Invalid Input**: An unpinned or hash-missing dependency MUST be rejected at resolution time, not installed unverified.
- **On System Error**: Fail closed — if the SBOM cannot be generated or a hash cannot be verified, the build fails rather than producing an unverified artifact.
- **Alerting**: SCA findings against SBOM components surface in CI (003); a hash mismatch is a hard build failure and SHOULD notify the security channel (`TO BE DECIDED`).

## Test Strategy
- **Unit Tests**: n/a (build configuration). Validate lockfile/hash presence with a config check.
- **Integration Tests**: Tamper a pinned hash in a test branch and assert install fails; add an unpinned dependency and assert the pinning check fails.
- **Security Tests**: Feed the SBOM to the SCA gate (003) and confirm components are evaluated for CVEs; confirm fail-closed on hash mismatch.
- **Compliance Tests**: SBOM artifact retained per build for audit; vetting records present for newly added dependencies.
- **Coverage Target**: ≥ 80% branch coverage applies to executable code; the pinning/SBOM checks are gating CI steps that MUST pass.

## Dependencies
- **Upstream**: 001 (manifests to pin), 002 (Docker build consumes pinned/hash-checked installs).
- **Downstream**: 003 (SCA consumes the SBOM and pinned set), all dependency-adding issues, `PRIV-1.14` breach-scoping.
- **External**: SBOM generator and lockfile/hashing toolchain (`TO BE DECIDED`); keep behind the generator/lockfile contract.

## Implementation Notes
- **Constraints**: Pin direct AND transitive dependencies with hashes; SBOM format is substitutable (SPDX/CycloneDX) behind the generator. Minimize dependency count — prefer the platform/standard library over a new dependency (e.g. exemplar 055 uses the platform `URL` API rather than a parser dependency).
- **Anti-Patterns**: MUST NOT use floating version ranges or un-hashed installs; MUST NOT add a dependency without vetting (`SEC-9.1`); MUST NOT disable hash verification "to make CI pass"; MUST NOT bake the SBOM with secrets or personal data.
- **AI Development Guidance**: **Recommended model: ChatGPT 5.5.** Lockfile/hash configuration and SBOM tooling are standard, well-documented supply-chain tasks suited to a strong generalist. Human review MUST confirm transitive pinning and fail-closed hash verification, and approve each dependency-vetting record.
