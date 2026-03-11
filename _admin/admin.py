"""
Admin class: scan project root for all projects, classify (backend DRF/FastAPI/py,
frontend React, mobile React Native), build by type, then deploy to K8s.
"""
import os
import subprocess
from pathlib import Path

from _admin.bob_builder.docker_scanner import find_dockerfile_dirs, get_project_root
from _admin.gke_admin.deployer import _load_env
from _admin.project_discovery import discover_projects
# DockerAdmin / GkeDeployer imported lazily in _get_docker / _get_deployer
from _admin.project_classifier import (
    BACKEND_DRF,
    BACKEND_FASTAPI,
    BACKEND_PY,
    FRONTEND_REACT,
    MOBILE_REACT_NATIVE,
    UNKNOWN,
)

try:
    from _admin.bob_builder.artifact_registry.artifact_admin import ArtifactAdmin
except Exception:
    ArtifactAdmin = None


class Admin:
    """
    Single entry point: discover projects -> classify -> build (by type) -> deploy to K8s.
    - Scan: all dirs with Dockerfile + dirs with package.json / manage.py / requirements.txt.
    - Classify: backend_drf, backend_fastapi, backend_py, frontend_react, mobile_react_native.
    - Build: if Dockerfile -> docker build; if frontend_react (no Dockerfile) -> npm run build; else skip.
    - Deploy: via gke_admin; LOCAL=true for local cluster.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        tag: str = "latest",
        local: bool | None = None,
    ):
        _load_env()
        root = project_root or get_project_root()
        self.project_root = root.resolve() if hasattr(root, "resolve") else Path(root).resolve()
        self.tag = tag
        self.local = local if local is not None else self._env_local()
        self._docker = None
        self._deployer = None

    def _get_docker(self):
        if self._docker is None:
            from _admin.bob_builder._docker.docker_admin import DockerAdmin
            self._docker = DockerAdmin()
        return self._docker

    def _get_deployer(self):
        if self._deployer is None:
            from _admin.gke_admin.deployer import GkeDeployer
            self._deployer = GkeDeployer(local=self.local)
        return self._deployer

    def _env_local(self) -> bool:
        v = os.environ.get("LOCAL", "").strip().lower() or os.environ.get("DEPLOY_LOCAL", "").strip().lower()
        return v in ("true", "1", "yes")

    def scan_dockerfiles(self) -> list[tuple[Path, str]]:
        """Collect all (dir_path, image_name) that contain a Dockerfile (merged from bob_builder)."""
        return find_dockerfile_dirs(self.project_root)

    def scan_projects(self) -> list[tuple[Path, str, str, bool]]:
        """
        Discover and classify all projects under project root.
        Returns list of (path, image_name, project_type, has_dockerfile).
        project_type: backend_drf | backend_fastapi | backend_py | frontend_react | mobile_react_native | unknown.
        """
        return discover_projects(self.project_root)

    def build_all(
        self,
        build_frontend_npm: bool = True,
        build_backend_docker_only: bool = True,
        force_rebuild: bool = False,
        packages_filter: list[str] | None = None,
    ) -> list[tuple[Path, str]]:
        """
        For each discovered project: classify, then build by type.
        - packages_filter: if set, only build projects whose dir name is in this list (e.g. MiracleAI, qbrain, qdash).
        - has_dockerfile -> docker build (all types); skip if image already exists unless force_rebuild.
        - frontend_react without Dockerfile -> npm run build if build_frontend_npm.
        - mobile_react_native without Dockerfile -> npm run build if build_frontend_npm.
        - backend_* without Dockerfile -> skip if build_backend_docker_only (default).
        Returns list of (dir_path, image_name) that produced a Docker image (for deploy).
        """
        projects = self.scan_projects()
        if packages_filter:
            allowed = {s.strip() for s in packages_filter if s}
            projects = [(p, n, t, d) for p, n, t, d in projects if p.name in allowed]
        if not projects:
            print(f"[Admin] No projects discovered under {self.project_root}")
            return []

        built = []
        for dir_path, image_name, project_type, has_docker in projects:
            try:
                rel = dir_path.relative_to(self.project_root)
            except ValueError:
                rel = dir_path
            print(f"[Admin] {rel} -> {project_type}, has_dockerfile={has_docker}")

            if has_docker:
                if not force_rebuild and self._get_docker().image_exists(image_name, self.tag):
                    print(f"[Admin] Image {image_name}:{self.tag} exists; skip build (use --force-rebuild to rebuild)")
                    built.append((dir_path, image_name))
                    continue
                full_tag = f"{image_name}:{self.tag}"
                try:
                    # qbrain/Dockerfile expects project root as context (COPY r.txt, manage.py, qbrain/)
                    context_dir = str(self.project_root) if dir_path.name == "qbrain" and (dir_path / "bm").is_dir() else None
                    self._get_docker().build_docker_image(
                        image_name=full_tag,
                        dockerfile_path=str(dir_path),
                        context_dir=context_dir,
                    )
                    built.append((dir_path, image_name))
                except Exception as e:
                    print(f"[Admin] Docker build failed for {dir_path}: {e}")
                continue

            if project_type in (FRONTEND_REACT, MOBILE_REACT_NATIVE) and build_frontend_npm:
                pkg = dir_path / "package.json"
                if pkg.exists():
                    try:
                        subprocess.run(
                            ["npm", "ci"] if (dir_path / "package-lock.json").exists() else ["npm", "install"],
                            cwd=dir_path,
                            check=False,
                            capture_output=True,
                        )
                        subprocess.run(["npm", "run", "build"], cwd=dir_path, check=True, capture_output=False)
                        print(f"[Admin] npm build ok: {rel}")
                    except subprocess.CalledProcessError as e:
                        print(f"[Admin] npm build failed for {dir_path}: {e}")
                    except FileNotFoundError:
                        print(f"[Admin] npm not found; skip npm build for {dir_path}")
                continue

            if project_type in (BACKEND_DRF, BACKEND_FASTAPI, BACKEND_PY) and not build_backend_docker_only:
                # No Dockerfile and we allow non-docker backend build: could run collectstatic / pip install here
                print(f"[Admin] Backend {project_type} has no Dockerfile; skip (set build_backend_docker_only=False to add custom step)")
        return built

    def push_to_registry(self, image_names: list[str], repo: str | None = None) -> list[str]:
        """
        Push local images to Artifact Registry (for GKE). Returns list of full image URIs.
        Requires GCP_PROJECT_ID, GCP_REGION in .env and gcloud configured.
        """
        if not ArtifactAdmin:
            print("[Admin] ArtifactAdmin not available; skip push.")
            return []

        uris = []
        for image_name in image_names:
            try:
                art = ArtifactAdmin(image_name=image_name, repo=repo or os.environ.get("GCP_ARTIFACT_REPO", "qfs-repo"))
                uri = f"{art.region}-docker.pkg.dev/{art.project_id}/{art.repo}/{image_name}:{self.tag}"
                art.tag_local_image(uri)
                art.push_image(uri)
                uris.append(uri)
            except Exception as e:
                print(f"[Admin] Push failed for {image_name}: {e}")
        return uris

    def deploy_all(
        self,
        image_names: list[str] | None = None,
        image_uris: list[str] | None = None,
        namespace: str = "default",
    ) -> list[tuple[str, bool]]:
        """
        Deploy images to the cluster (GKE or local per .env / LOCAL).
        - If image_uris is set, deploy those full URIs (e.g. after push to registry).
        - Else use image_names with self.tag (local image names for local cluster).
        """
        if image_uris:
            return self._get_deployer().deploy_all_by_uri(image_uris, namespace=namespace)
        names = image_names or []
        return self._get_deployer().deploy_all(names, tag=self.tag, namespace=namespace)

    def run(
        self,
        build: bool = True,
        push: bool | None = None,
        deploy: bool = True,
        namespace: str = "default",
        build_frontend_npm: bool = True,
        build_backend_docker_only: bool = True,
        force_rebuild: bool = False,
        packages_filter: list[str] | None = None,
    ) -> dict:
        """
        Full pipeline: discover & classify -> build by type -> (push if GKE) -> deploy.
        Deploy target: if self.local (env LOCAL=true) -> local K8s cluster; else -> cloud (GKE) using env vars.
        push: if None, push only when not LOCAL (GKE). Set False to skip push, True to force.
        packages_filter: if set, only build/deploy these package dir names (e.g. MiracleAI, qbrain, qdash).
        build_frontend_npm: run npm run build for frontend_react/mobile without Dockerfile.
        build_backend_docker_only: only build backend images that have a Dockerfile.
        force_rebuild: if True, rebuild Docker images even when they already exist locally.
        Returns dict with built, pushed_uris, deploy_results.
        """
        if build:
            built_pairs = self.build_all(
                build_frontend_npm=build_frontend_npm,
                build_backend_docker_only=build_backend_docker_only,
                force_rebuild=force_rebuild,
                packages_filter=packages_filter,
            )
        else:
            projects = self.scan_projects()
            if packages_filter:
                allowed = {s.strip() for s in packages_filter if s}
                projects = [(p, n, t, has_d) for p, n, t, has_d in projects if p.name in allowed]
            built_pairs = [(p, n) for p, n, _, has_d in projects if has_d]
        built_names = [name for _, name in built_pairs]

        pushed_uris = []
        do_push = push if push is not None else (not self.local)
        if deploy and built_names and not self.local:
            self._get_deployer().log_cloud_env()
        if do_push and built_names and ArtifactAdmin:
            pushed_uris = self.push_to_registry(built_names)

        deploy_results = []
        if deploy and built_names:
            if pushed_uris:
                deploy_results = self._get_deployer().deploy_all_by_uri(pushed_uris, namespace=namespace)
            else:
                deploy_results = self.deploy_all(image_names=built_names, namespace=namespace)

        return {
            "built": built_pairs,
            "pushed_uris": pushed_uris,
            "deploy_results": deploy_results,
        }


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Admin: discover projects, classify (backend/frontend/mobile), build by type, deploy to K8s"
    )
    parser.add_argument("--local", action="store_true", help="Deploy to local cluster (kubectl context); overrides .env LOCAL")
    parser.add_argument("--no-build", action="store_true", help="Skip build step")
    parser.add_argument("--no-deploy", action="store_true", help="Skip deploy step")
    parser.add_argument("--no-push", action="store_true", help="Do not push to Artifact Registry (GKE)")
    parser.add_argument("--no-npm-build", action="store_true", help="Do not run npm run build for frontend/mobile projects without Dockerfile")
    parser.add_argument("--tag", default="latest", help="Docker tag (default: latest)")
    parser.add_argument("--namespace", default="default", help="Kubernetes namespace")
    parser.add_argument("--scan-only", action="store_true", help="Only print discovered and classified projects, then exit")
    parser.add_argument("--force-rebuild", action="store_true", help="Rebuild Docker images even if they already exist locally")
    args = parser.parse_args()

    admin = Admin(tag=args.tag, local=args.local if args.local else None)

    if args.scan_only:
        for path, image_name, project_type, has_docker in admin.scan_projects():
            rel = path.relative_to(admin.project_root) if admin.project_root in path.parents or path == admin.project_root else path
            print(f"  {rel} -> image={image_name} type={project_type} dockerfile={has_docker}")
        raise SystemExit(0)

    out = admin.run(
        build=not args.no_build,
        push=None if not args.no_push else False,
        deploy=not args.no_deploy,
        namespace=args.namespace,
        build_frontend_npm=not args.no_npm_build,
        force_rebuild=args.force_rebuild,
    )
    print("[Admin] Built (images):", len(out["built"]))
    print("[Admin] Pushed:", len(out["pushed_uris"]))
    print("[Admin] Deploy results:", out["deploy_results"])
