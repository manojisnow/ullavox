# Releasing Ullavox

Release work belongs on a branch and goes through a PR. Do not edit the default
branch directly. Validate the packaged app and record acceptance evidence. A release
tag triggers public image publication, so push it only after maintainer release
approval.

## Prepare a candidate

1. Update the Ullavox image tag in `docker-compose.release.yml` to the target
   version. Keep README's generic install pointed at the latest published release
   asset, and put an exact tag URL in the curated notes at
   `docs/releases/vX.Y.Z.md`. Keep the UI version marker unchanged unless a
   separate change is requested.
2. Run source quality gates and build the production Dockerfile. Validate
   `docker compose -f docker-compose.release.yml config`. For a version not yet
   published, use a separate Compose override selecting the local candidate
   image with `pull_policy: never`; do not push a candidate to the final image
   tag to make the test work.
3. Start the release Compose stack under an isolated project name and unused
   localhost ports. Verify the Ollama health check, one-time default-model
   download, app health and bundled frontend. Never select production volumes
   or stop unrelated containers for this test.
4. Test a fresh database and a SQLite backup of an existing database. Use
   SQLite's backup API for a live source, retain its original rows, and compare
   them after startup and restart. Copies contain private data and stay outside
   the repository. Validate ordinary chat, file analysis and follow-ups, web
   research, and persistence with the shipped model.
5. Run `python3 scripts/verify-release-package.py --base http://localhost:PORT`
   against each packaged app. The default model is `granite4:3b`; a different
   model requires `--model`. The script creates test conversations and stores
   raw responses under `/tmp`. Failures are release-readiness findings, not
   reasons to weaken checks. Run local-model checks sequentially when apps
   share one Ollama server. Validate streaming chat, cancellation and UI
   behavior manually as well.
6. Record the candidate commit, image ID, platform, test outcomes and remaining
   limitations. Local ARM64 checks do not prove AMD64 behavior. Include manual
   packaged-app acceptance in the validation record. Open a reviewable PR and
   verify CI on the final head and merged commit, including Secret scanning,
   before publication.

## Publish and verify

After approval, create `vX.Y.Z` at the reviewed merge commit and push that exact
tag. `.github/workflows/release.yml` runs backend quality gates, frontend
coverage/build and Dockerfile lint, then publishes AMD64 and ARM64 images to
Docker Hub and creates a GitHub release with the Compose asset and curated
notes. It requires the configured Docker Hub credentials. Existing runtime
package versions do not determine the release version; the Git tag does.

Watch the Release workflow until it succeeds. Confirm the `X.Y.Z` manifest
contains both platforms, the downloaded Compose asset selects `X.Y.Z`, and the
GitHub release includes the limits and backup instructions. Pull the published
image and perform a final isolated smoke test. A successful source build alone
is not confirmation that publication succeeded. Do not move an existing release
tag or silently overwrite a published version to repair a failed release.

Keep the prior image and database backup until the upgrade is accepted. Follow
the target release notes for rollback and preserve Docker's Compose project
name so the expected named volumes are selected.

## Stable and prerelease publication rules

Release publication is tag-triggered. There is no manual Release dispatch from a
branch. Use **Sync Docker Hub README** for documentation changes; a failed release
can be retried from its original tag run after reviewing the failure.

Before any registry login, the validation job requires a tag push, validates the
version, checks that its commit belongs to default-branch history, and verifies
that the release Compose app image pins that exact version. The existing build
and quality gates must also pass before publishing.

| Pushed tag | Docker tags | GitHub release |
| --- | --- | --- |
| `v1.8.0` | `1.8.0`, `1.8`, `latest` | Stable, marked latest |
| `v1.8.0-rc.1` | `1.8.0-rc.1` only | Prerelease, not latest |

Core numeric components and numeric prerelease identifiers cannot have leading
zeros. Build metadata (`+...`) is unsupported because it cannot be preserved in a
Docker tag. The complete image tag must fit Docker's 128-character limit.

For a prerelease, pin `docker-compose.release.yml` to that exact prerelease image
and prepare matching notes such as `docs/releases/v1.8.0-rc.1.md`. Prereleases skip
Docker Hub description sync and cannot update minor/latest image aliases. Before
the stable tag, update the Compose pin and release notes to the stable version.

Run the publication regression checks locally with:

```bash
python3 -m unittest discover -s scripts/tests -p 'test_release_policy.py' -v
```

CI runs these checks on PRs and main. These safeguards apply to tags containing
this workflow revision. Historical workflow runs retain their original code;
do not rerun an older release workflow merely to refresh documentation or tags.

## Refresh Docker Hub documentation

After README corrections are merged, run **Sync Docker Hub README**
(`.github/workflows/dockerhub-readme.yml`) from the default branch in GitHub
Actions. It copies the default branch README and repository description to
`dumanoj/ullavox`, converting relative links to absolute URLs. Runs from other
branches skip the sync job.

This manual workflow uses the existing `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`
Actions secrets internally to authenticate to Docker Hub. It has read-only GitHub
contents permissions and does not build images, update image tags, or create a
release. Do not use a manual Release workflow run for documentation-only changes.
After a successful sync, verify the public Docker Hub README and links.
