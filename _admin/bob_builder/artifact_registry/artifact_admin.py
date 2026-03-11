import os
import subprocess

from qbrain.auth.load_sa_creds import load_service_account_credentials
from qbrain.utils.run_subprocess import exec_cmd, pop_cmd
from google.cloud import artifactregistry_v1
import dotenv
dotenv.load_dotenv()

class ArtifactAdmin:



    def __init__(self, **kwargs):
        # IMAGE SETTINGS
        self.project_id = kwargs.get("project_id") or os.environ["GCP_PROJECT_ID"]
        self.region = kwargs.get("region") or os.environ["GCP_REGION"]
        self.repo = kwargs.get("repo", "qfs-repo")

        # RAY cluster image
        self.image_name = kwargs.get("image_name", "qfs")
        self.tag = 'latest'

        self.source = kwargs.get('source', '')
        self.cluster_name = os.environ.get("GKE_SIM_CLUSTER_NAME", "")
        self.deployment_name = kwargs.get('deployment_name', 'cluster-deployment')
        self.container_port = int(os.environ.get("CLUSTER_PORT", "8080"))
        self.full_tag = None

        # Credentials: use provided or load from SA
        creds = kwargs.get("credentials") or load_service_account_credentials()
        self.client = artifactregistry_v1.ArtifactRegistryClient(credentials=creds)

        self.parent = f"projects/{self.project_id}/locations/{self.region}/repositories/{self.repo}/packages/{self.image_name}"

    def tag_local_image(
            self,
            image_uri:str
    ) -> str:
        """
        Tags a local Docker image with the required Artifact Registry path.

        Returns: The full remote destination path (e.g., us-central1-docker.pkg.dev/...)
        """
        exec_cmd(cmd = ["docker", "tag", self.image_name, image_uri])

    def push_image(self, remote_path: str):
        """
        Pushes the tagged image to Artifact Registry.
        This command performs the upsert (only uploads new layers).
        """
        print(f"3. Pushing image to Artifact Registry...")
        pop_cmd(cmd = ["docker", "push", remote_path])




    def get_latest_image(self) -> str:
        """Get img uri from artifact registry using the official client library"""
        print("start get_latest_image (Client Library)...")

        self.ensure_image_exists()
        try:
            # 3. Versionen abfragen (sortiert nach Update-Zeit)
            # Wir listen die Versionen des Pakets (Images) auf
            request = artifactregistry_v1.ListVersionsRequest(
                parent=self.parent,
                order_by="update_time desc",
                page_size=1
            )

            page_result = self.client.list_versions(request=request)

            # Den ersten Treffer nehmen
            for version in page_result:
                # Die URI zusammenbauen: region-docker.pkg.dev/project/repo/image@sha256:hash
                # Oder einfacher mit dem Tag, falls vorhanden:
                version_id = version.name.split('/')[-1]
                image_uri = f"{self.region}-docker.pkg.dev/{self.project_id}/{self.repo}/{self.image_name}@{version_id}"

                print(f"  -> Latest image found: {image_uri}")
                return image_uri

        except Exception as e:
            print(f"  [!!!] Error fetching image from Artifact Registry: {e}")

        # Fallback, falls keine Version gefunden wurde oder ein Fehler auftrat
        fallback = "docker.io/library/hello-world"
        print(f"  -> Using fallback image: {fallback}")
        return fallback

    def list_all_images_artifact_registry(self) -> list[str]:
        """
        Gibt alle Images (URIs) in der Artifact Registry zurück.
        """
        cmd = f"gcloud artifacts docker images list us-central1-docker.pkg.dev/{self.project_id}/{self.repo} --format=\"value(uri)\""

        images = exec_cmd(cmd)

        if not images:
            print("⚠️ Keine Images in Artifact Registry gefunden.")
            return []

        print("Gefundene Images:")
        for img in images:
            print(" -", img)

        return images

    def delete_all_images(self, repo: str):
        """
        Löscht alle Images eines Artifact Registry Repositories.

        Args:
            repo (str): Name des Repos (z.B. "qfs-repo").
            location (str): Region (z.B. "us-central1").
            project (str): GCP Projekt-ID (z.B. "my-project").
        """
        try:
            # Liste aller Image-Tags im Repo abrufen
            cmd_list = [
                "gcloud", "artifacts", "docker", "images", "list",
                f"{self.region}-docker.pkg.dev/{self.project_id}/{repo}",
                "--format=value(IMAGE)"
            ]

            result = exec_cmd(cmd_list)
            images = result.splitlines()

            if not images:
                print(f"Keine Images im Repo {repo} gefunden.")
                return

            for image in images:
                print(f"Lösche {image} ...")
                com = ["gcloud", "artifacts", "docker", "images", "delete", image, "--quiet", "--delete-tags"]
                result = exec_cmd(com)
            print("Alle Images gelöscht.")
        except subprocess.CalledProcessError as e:
            print("Fehler beim Löschen:", e.stderr)

    def _repo_exists(self, repo_name: str, project_id: str = None, location: str = None) -> bool:
        """Check if a repository exists using the client."""
        project_id = project_id or self.project_id
        location = location or self.region
        parent = f"projects/{project_id}/locations/{location}"
        try:
            req = artifactregistry_v1.ListRepositoriesRequest(parent=parent, page_size=1000)
            for repo in self.client.list_repositories(request=req):
                if repo.name.split("/")[-1] == repo_name:
                    return True
        except Exception:
            pass
        return False

    def create_repository(
        self,
        repo_id: str = None,
        format_mode: str = "DOCKER",
        project_id: str = None,
        location: str = None,
    ):
        """
        Create an Artifact Registry repository using the client.
        Uses credentials from ArtifactAdmin. Skips if repo already exists.

        Args:
            repo_id: Repository name (default: self.repo)
            format_mode: DOCKER, MAVEN, NPM, PYTHON, APT, YUM, etc.
            project_id: Override project (default: self.project_id)
            location: Override location (default: self.region)
        """
        repo_id = repo_id or self.repo
        project_id = project_id or self.project_id
        location = location or self.region
        parent = f"projects/{project_id}/locations/{location}"

        if self._repo_exists(repo_id, project_id, location):
            print(f"Repository '{repo_id}' already exists.")
            return

        # Resolve format enum: Repository.Format.DOCKER, etc.
        Repository = getattr(artifactregistry_v1, "Repository", None) or getattr(
            getattr(artifactregistry_v1, "types", object()), "Repository", None
        )
        fmt_enum = 1  # DOCKER default
        if Repository and hasattr(Repository, "Format"):
            fmt_enum = getattr(Repository.Format, format_mode.upper(), getattr(Repository.Format, "DOCKER", 1))

        repo_obj = Repository(format_=fmt_enum) if Repository else None
        if repo_obj is None:
            types = getattr(artifactregistry_v1, "types", artifactregistry_v1)
            repo_obj = types.Repository(format_=fmt_enum)

        req = artifactregistry_v1.CreateRepositoryRequest(
            parent=parent,
            repository_id=repo_id,
            repository=repo_obj,
        )
        op = self.client.create_repository(request=req)
        result = op.result()
        print(f"Created repository '{repo_id}': {result.name}")

    def ensure_repo_exists(
        self,
        repo_id: str = None,
        format_mode: str = "DOCKER",
        project_id: str = None,
        location: str = None,
    ):
        """
        Ensure repository exists; create it if not. Uses ArtifactAdmin credentials.
        """
        repo_id = repo_id or self.repo
        if self._repo_exists(repo_id, project_id, location):
            return
        self.create_repository(repo_id=repo_id, format_mode=format_mode, project_id=project_id, location=location)

    def _image_exists_in_repo(self, image_name: str, repo_name: str = None) -> bool:
        """Check if a Docker image (package) exists in the repo."""
        repo_name = repo_name or self.repo
        parent = f"projects/{self.project_id}/locations/{self.region}/repositories/{repo_name}"
        try:
            pkg_req = artifactregistry_v1.ListPackagesRequest(parent=parent, page_size=1000)
            for pkg in self.client.list_packages(request=pkg_req):
                if pkg.name.split("/")[-1] == image_name:
                    return True
        except Exception:
            pass
        return False

    def ensure_image_exists(
        self,
        image_name: str = None,
        repo_name: str = None,
        default_source: str = "docker.io/library/hello-world:latest",
    ):
        """
        Ensure the Docker image exists in Artifact Registry. Creates repo if needed.
        If image does not exist, pulls default_source, tags it, and pushes.
        Uses ArtifactAdmin credentials for registry auth (docker must be configured).
        """
        image_name = image_name or self.image_name
        repo_name = repo_name or self.repo

        # CHECK REPOS
        self.ensure_repo_exists(repo_id=repo_name)

        if self._image_exists_in_repo(image_name, repo_name):
            print(f"Image '{image_name}' already exists in repo '{repo_name}'.")
            return

        remote_uri = f"{self.region}-docker.pkg.dev/{self.project_id}/{repo_name}/{image_name}:latest"
        print(f"Image '{image_name}' not found. Pulling {default_source}, tagging and pushing to {remote_uri}...")
        pop_cmd(cmd=["docker", "pull", default_source])
        exec_cmd(cmd=["docker", "tag", default_source, remote_uri])
        self.push_image(remote_uri)
        print(f"Image '{image_name}' created and pushed.")

    def _collect_all_resources_via_client(self, project_id: str = None, location: str = None) -> dict:
        """
        Collect all Artifact Registry resources for a project using the client (no exec).
        Returns dict with repos, packages, versions, files, and docker_images.
        """
        project_id = project_id or self.project_id
        location = location or self.region
        parent = f"projects/{project_id}/locations/{location}"

        result = {"repos": [], "packages": [], "versions": [], "files": [], "docker_images": []}

        try:
            # 1. List repositories
            req = artifactregistry_v1.ListRepositoriesRequest(parent=parent, page_size=1000)
            for repo in self.client.list_repositories(request=req):
                repo_name = repo.name.split("/")[-1]
                repo_format = str(repo.format_) if hasattr(repo, "format_") else "unknown"
                result["repos"].append({"name": repo_name, "full_name": repo.name, "format": repo_format})
                print(f"  [REPO] {repo_name} ({repo.name})")

                # 2a. For Docker repos: list docker images directly (if API available)
                is_docker = "DOCKER" in repo_format.upper()
                ListDockerImagesRequest = getattr(artifactregistry_v1, "ListDockerImagesRequest", None)
                if is_docker and ListDockerImagesRequest and hasattr(self.client, "list_docker_images"):
                    try:
                        docker_req = ListDockerImagesRequest(parent=repo.name, page_size=1000)
                        for img in self.client.list_docker_images(request=docker_req):
                            img_name = getattr(img, "uri", img.name) or img.name
                            result["docker_images"].append({"uri": img_name, "repo": repo_name})
                            print(f"    [DOCKER_IMAGE] {img_name}")
                    except Exception as de:
                        print(f"    (docker images list error: {de})")

                # 2b. List packages (for non-Docker or as fallback)
                try:
                    pkg_req = artifactregistry_v1.ListPackagesRequest(parent=repo.name, page_size=1000)
                    for pkg in self.client.list_packages(request=pkg_req):
                        pkg_name = pkg.name.split("/")[-1]
                        result["packages"].append({"name": pkg_name, "full_name": pkg.name, "repo": repo_name})
                        print(f"    [PACKAGE] {pkg_name}")

                        # 3. List versions in this package
                        try:
                            ver_req = artifactregistry_v1.ListVersionsRequest(parent=pkg.name, page_size=1000)
                            for ver in self.client.list_versions(request=ver_req):
                                ver_id = ver.name.split("/")[-1]
                                result["versions"].append({"id": ver_id, "full_name": ver.name, "package": pkg_name})
                                print(f"      [VERSION] {ver_id}")
                        except Exception as ve:
                            print(f"      (versions list error: {ve})")

                        # 4. List files in this package (if supported)
                        try:
                            file_req = artifactregistry_v1.ListFilesRequest(parent=pkg.name, page_size=1000)
                            for f in self.client.list_files(request=file_req):
                                fname = f.name.split("/")[-1]
                                result["files"].append({"name": fname, "full_name": f.name, "package": pkg_name})
                                print(f"      [FILE] {fname}")
                        except Exception:
                            pass  # Many package types don't have files
                except Exception as pe:
                    print(f"    (packages list error: {pe})")

        except Exception as e:
            print(f"[!!!] Error collecting resources: {e}")
            import traceback
            traceback.print_exc()

        return result

    def test_view_list_all_resources(self, project_id: str = None, location: str = None) -> dict:
        """
        Test view: collects all Artifact Registry resources (repos, packages, versions, files)
        for the project using the client only. Prints everything to console.
        """
        project_id = project_id or self.project_id
        location = location or self.region
        print(f"\n=== ArtifactAdmin Test View: All Resources ===")
        print(f"Project: {project_id} | Location: {location}")
        print("-" * 60)

        result = self._collect_all_resources_via_client(project_id=project_id, location=location)

        print("-" * 60)
        print(f"Summary: {len(result['repos'])} repos, {len(result['packages'])} packages, "
              f"{len(result['versions'])} versions, {len(result['files'])} files, "
              f"{len(result.get('docker_images', []))} docker images")
        print("=" * 60)
        return result


if __name__ == "__main__":
    registry = ArtifactAdmin()
    #registry.get_latest_image()
    # Test view: list all project resources via client
    registry.get_latest_image()
