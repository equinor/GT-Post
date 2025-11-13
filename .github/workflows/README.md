# CI/CD Pipeline

This document describes the CI/CD setup used by this repository. The pipeline follows the same principles used in `equinor/delft3d4-pepm` and is composed of: automated tests, automated releases, and container build/publish workflows.

**Workflows present**

 - `build-and-test.yml` (named `GT-Post Python Tests` in the workflow): runs the test suite on push and pull requests. It uses a matrix across `ubuntu-latest`, `macOS-latest`, and `windows-latest` and sets up Python 3.11 and Pixi before running `pixi run test`.
- `release-please.yml`: runs on pushes to `main` and uses `googleapis/release-please-action` to create or update GitHub releases (release-please). It authenticates using a GitHub App token (see Secrets/Vars below).
- `build-and-publish.yml`: a reusable workflow (invokable by `workflow_call`) that builds and pushes Docker images to a registry. It expects inputs: `Registry`, `Tag`, `ImageName`, and `WorkingDir`.
- `publish-package.yml`: runs when a GitHub Release is created and directly calls `build-and-publish.yml` to build and publish container images using the release's `tag_name` and repository name.

How these pieces fit together

- Developer pushes changes / opens a PR → `build-and-test.yml` runs the tests across OS matrix.
- Merges to `main` → `release-please.yml` runs and may create or update a GitHub Release (depending on commit messages and the release-please configuration in `release-please-config.json`).
- When a Release is created (manually or by release-please), `publish-package.yml` runs and directly calls `build-and-publish.yml` with:
  - `ImageName` set to the full repository name (e.g., `equinor/gt-post`)
  - `Tag` set to the release's `tag_name`
  - `WorkingDir` set to `.` (repository root)
  - The workflow builds and pushes the container to the configured registry.

Important details and operator notes

- Release-please authentication: `release-please.yml` uses a GitHub App for auth. You must configure the repository/organization variables and secrets referenced in the workflow:
  - Repository variable: `PEPM_CI_APP_ID` (GitHub App ID)
  - Repository secret: `PEPM_CI_APP_SECRET` (private key / PEM for the GitHub App)

- Container registry login: `build-and-publish.yml` uses the `GITHUB_TOKEN` (workflow default) to login to the registry provided in the `Registry` input. For GHCR (GitHub Container Registry) this is typically sufficient for org-owned images; for external registries you may need to pass credentials via secrets.

- Image naming and tags:
  - `publish-package.yml` uses `github.repository` for the `ImageName` (e.g., `equinor/gt-post`).
  - The `Tag` value is taken directly from `github.event.release.tag_name`. Example: `v1.2.3` → tag `v1.2.3`.
  - `build-and-publish.yml` pushes two tags: the provided `${Tag}` and `latest`.

- Reusable workflow usage: to add a new image/component to publish, call the `build-and-publish.yml` workflow with the required inputs and make sure `WorkingDir` points to the folder containing the `Dockerfile` you want to build.

Local testing and common commands

- Run unit tests locally (recommended: use Python 3.11 and Pixi):

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pixi
pixi install
pixi run -- pytest --verbose
```

- Run the CI test job locally (approximate): use `pixi run test` as defined in `pyproject.toml` tasks.

- Build and test Docker image locally (example):

```bash
docker build -t gtpost-local:latest .
```

How to trigger a publish manually

1. Create a GitHub Release (via the UI or API) with a tag name. `publish-package.yml` will run for `release: created` events.
2. The workflow uses `github.repository` for the image name and `github.event.release.tag_name` for the image tag.
3. The image will be pushed to GHCR at `ghcr.io/<repository>:<tag>` and `ghcr.io/<repository>:latest`.

Troubleshooting

- If images are not pushed: check `GITHUB_TOKEN` permissions and whether the repository is allowed to push to the target registry. For GHCR, ensure `packages: write` permission is granted in the workflow (it is in `build-and-publish.yml`).
- If release-please fails: verify `PEPM_CI_APP_ID` and `PEPM_CI_APP_SECRET` are set and that the GitHub App has the required permissions and installations.
- If the wrong image name is used: the workflow uses `github.repository` which returns the full repo path (e.g., `equinor/gt-post`).

Quick troubleshooting checklist

- Confirm `GITHUB_TOKEN` has `packages: write` and `contents: read` in the container publish workflow.
- Ensure `PEPM_CI_APP_ID` (variable) and `PEPM_CI_APP_SECRET` (secret) exist when using `release-please`.
- For GHCR pushes: verify repository visibility and package write permissions for the token used.
- The workflow uses `github.repository` for image name and `github.event.release.tag_name` for tag - no custom parsing needed.

References

- `./.github/workflows/build-and-test.yml`
- `./.github/workflows/build-and-publish.yml`
- `./.github/workflows/publish-package.yml`
- `./.github/workflows/release-please.yml`
- See `equinor/delft3d4-pepm` for an example of these pipelines applied to a different project.
