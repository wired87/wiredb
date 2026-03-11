from qbrain.auth.set_gcp_auth_creds_path import set_gcp_auth_path
from _admin.bob_builder._docker.docker_admin import DockerAdmin
from _admin.bob_builder.artifact_registry.artifact_admin import ArtifactAdmin
from _admin.bob_builder.docker_scanner import find_dockerfile_dirs, get_project_root


def build_all_dockerfiles(project_root=None, tag: str = "latest"):
    """
    Scan project root for every directory that contains a Dockerfile, then build
    a Docker image from each. Image name is derived from the directory name.

    Args:
        project_root: Root directory to scan (default: parent of bob_builder).
        tag: Tag to apply to each image (default "latest").
    Returns:
        List of (dir_path, image_name) that were built successfully.
    """
    root = project_root or get_project_root()
    pairs = find_dockerfile_dirs(root)
    if not pairs:
        print(f"No directories with a Dockerfile found under {root}")
        return []

    docker_admin = DockerAdmin()
    built = []
    for dir_path, image_name in pairs:
        full_tag = f"{image_name}:{tag}"
        print(f"[bob_builder] Building {dir_path.relative_to(root)} -> {full_tag}")
        try:
            docker_admin.build_docker_image(
                image_name=full_tag,
                dockerfile_path=str(dir_path),
            )
            built.append((dir_path, image_name))
        except Exception as e:
            print(f"[bob_builder] Build failed for {dir_path}: {e}")
    return built


def build_and_deploy_workflow(
    dockerfile_path=r"C:\Users\bestb\PycharmProjects\jax_test\Dockerfile",
    image_name: str = "core",
    repo: str = "core",
    deploy_to_kub: bool = False,
):
    """
    Builds a Docker image, pushes it to Google Artifact Registry,
    and deploys it to GKE using KubeRay.
    """
    # --- 1. Configuration ---
    artifact_admin = ArtifactAdmin(image_name=image_name, repo=repo)
    docker_admin = DockerAdmin()

    # Construct the full image URI for Artifact Registry
    image_uri = (
        f"{artifact_admin.region}-docker.pkg.dev/"
        f"{artifact_admin.project_id}/"
        f"{artifact_admin.repo}/"
        f"{artifact_admin.image_name}:{artifact_admin.tag}"
    )

    # Ensure Docker is logged in against the Artifact Registry host.
    #docker_admin.login_to_artifact_registry(region=artifact_admin.region)

    # Build a local image using the short image_name (e.g. "core").
    docker_admin.build_docker_image(
        image_name=artifact_admin.image_name,
        dockerfile_path=dockerfile_path,
    )


    # --- 4. Push the Docker Image to Artifact Registry ---
    print(f"Pushing image to Artifact Registry: {image_uri}")
    artifact_admin.tag_local_image(image_uri)
    artifact_admin.push_image(remote_path=image_uri)



    # --- OPTIONAL: Deploy to GKE with KubeRay ---
    print("Deploying to GKE with KubeRay...")
    latest_image_from_registry = artifact_admin.get_latest_image()
    if latest_image_from_registry and deploy_to_kub:
        print(f"Deploying latest image: {latest_image_from_registry}")
        # kuberay_manager.deploy(latest_image_from_registry) # Example call
    else:
        print("Could not retrieve the latest image from the registry. Deployment aborted.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1].strip().lower() == "all":
        # Build all images from any directory under project root that has a Dockerfile
        build_all_dockerfiles()
    else:
        # Ensure application default credentials are set before any gcloud / Docker calls.
        set_gcp_auth_path()
        build_and_deploy_workflow()