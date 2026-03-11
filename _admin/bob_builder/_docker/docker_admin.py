import os
import subprocess
import sys

from _admin.bob_builder._docker.dockerfile import get_custom_dockerfile_content
from _admin.bob_builder._docker.dynamic_docker import generate_dockerfile
from qbrain.utils.run_subprocess import pop_cmd


class DockerAdmin:
    """
    Thin wrapper around the `docker` CLI.

    We intentionally avoid the Python Docker Engine API client and instead
    shell out to `docker` so that behavior is consistent across Windows
    and Linux. Minor OS-specific handling is controlled via `os.name`.
    """

    def __init__(self, allow_no_daemon: bool = False):
        # We keep the allow_no_daemon parameter for backward compatibility,
        # but CLI-based calls simply fail with clear messages if Docker
        # isn't installed or the daemon isn't running.
        self.allow_no_daemon = allow_no_daemon
        self.is_windows = os.name == "nt"
        # On both Windows and Linux we expect `docker` to be on PATH.
        self.docker_bin = "docker"

    def login_to_artifact_registry(self, region: str):
        """Authenticates Docker with Google Artifact Registry."""
        print(f"Configuring Docker for Artifact Registry in region: {region}")
        try:
            cmd = ["gcloud", "auth", "configure-docker", f"{region}-docker.pkg.dev", "--quiet"]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Docker authenticated with Artifact Registry successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to authenticate with Artifact Registry: {e.stderr}")
            raise
        except FileNotFoundError:
            print("'gcloud' command not found. Is the Google Cloud SDK installed and in your PATH?")
            raise


    def build_docker_image(
        self,
        image_name: str,
        dockerfile_path: str = ".",
        env: dict | None = None,
        context_dir: str | None = None,
    ):
        """
        Build a Docker image using a specific Dockerfile.

        Args:
            image_name: Tag to apply to the built image (e.g. "core").
            dockerfile_path: Absolute or relative path to the Dockerfile or directory containing it.
            env: Optional environment variables to inject via --build-arg.
            context_dir: Optional build context directory. If set, used instead of Dockerfile directory
                (e.g. for qbrain/Dockerfile which must be built with project root as context).
        """
        dockerfile_path = os.path.abspath(dockerfile_path)
        if os.path.isdir(dockerfile_path):
            dockerfile_dir = dockerfile_path
            dockerfile_path = os.path.join(dockerfile_path, "Dockerfile")
        else:
            dockerfile_dir = os.path.dirname(dockerfile_path) or "."
        use_context = os.path.abspath(context_dir) if context_dir else dockerfile_dir

        cmd = [self.docker_bin, "build", "-t", image_name, "-f", dockerfile_path]

        if env:
            for name, val in env.items():
                cmd += ["--build-arg", f"{name}={val}"]

        cmd.append(use_context)
        print("Running docker build:", " ".join(cmd))
        pop_cmd(cmd)


    def run_local_docker_image(
            self,
            image: str,
            name: str = None,
            ports: dict = None,
            env: dict = None,
            detach: bool = True
    ) -> str:
        """
        Run a local Docker image for testing.
        """
        try:
            cmd = ["docker", "run"]
            if detach: cmd.append("-d")
            if name: cmd += ["--name", name]
            if ports:
                for host_port, container_port in ports.items():
                    cmd += ["-p", f"{host_port}:{container_port}"]
            if env:
                for k, v in env.items():
                    cmd += ["-e", f"{k}={v}"]
            cmd.append(image)

            print("Running local docker container:", " ".join(cmd))
            container_id = subprocess.check_output(cmd, text=True).strip()
            print(f"✅ Started container {container_id[:12]} from {image}")
            return container_id
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to run docker image: {e}")
            return None

    def create_static_dockerfile(
        self,
        base_ray_image: str,
        requirements_file: str,
        app_script_name: str
    ):
        content = get_custom_dockerfile_content(
            base_ray_image=base_ray_image,
            requirements_file=requirements_file,
            app_script_name=app_script_name
        )
        self._write_dockerfile(content)
        print(f"✅ Static Dockerfile erstellt: {self.dockerfile_path}")

    def create_dynamic_dockerfile(self, project_root, startup_cmd, **env_vars):
        content = generate_dockerfile(
            project_root=project_root,
            startup_cmd=startup_cmd,
            **env_vars
        )
        print(f"✅ Dynamic Dockerfile erstellt: {self.dockerfile_path}")
        return content

    def build_image(self, path, image_name: str):
        """
            Builds a Docker image using the given tag and context path.

            Args:
                tag: The tag for the Docker image (e.g., 'qfs').
                context_path: The build context path (e.g., '.').
            """
        command = [self.docker_bin, "build", "-t", image_name, path]
        print(f"Running command: {' '.join(command)}")
        try:
            # Use subprocess.run to execute the command.
            # check=True raises a CalledProcessError if the command returns a non-zero exit code.
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            # Stream the output in real-time
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')

            process.wait()

            if process.returncode != 0:
                print(f"Error: Docker build failed with exit code {process.returncode}", file=sys.stderr)
                sys.exit(1)

            print("\nDocker image built successfully!")

        except FileNotFoundError:
            print("Error: 'docker' command not found. Is Docker installed and in your PATH?", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred: {e}", file=sys.stderr)
            sys.exit(1)

    def force_build_image(self, image_name: str, tag: str = "latest", context_path: str = "."):
        """
        Force-build an image using the docker CLI.

        Equivalent to:
            docker build -t image_name:tag context_path
        """
        full_tag = f"{image_name}:{tag}"
        command = [self.docker_bin, "build", "-t", full_tag, context_path]
        print(f"Running command: {' '.join(command)}")
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if process.stdout:
                for line in iter(process.stdout.readline, ""):
                    print(line, end="")
            process.wait()
            if process.returncode != 0:
                print(
                    f"Error: Docker force-build failed with exit code {process.returncode}",
                    file=sys.stderr,
                )
                if not self.allow_no_daemon:
                    sys.exit(process.returncode)
            else:
                print(f"\nDocker image built successfully: {full_tag}")
        except FileNotFoundError:
            print(
                "Error: 'docker' command not found. Is Docker installed and in your PATH?",
                file=sys.stderr,
            )
            if not self.allow_no_daemon:
                sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during force_build_image: {e}", file=sys.stderr)
            if not self.allow_no_daemon:
                sys.exit(1)

    def image_exists(self, image_name: str, tag: str = "latest") -> bool:
        """
        Check if an image with the given tag exists locally using the docker CLI.

        Uses:
            docker image inspect image_name:tag
        """
        full_tag = f"{image_name}:{tag}"
        command = [self.docker_bin, "image", "inspect", full_tag]
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            print(
                "Error: 'docker' command not found while checking image existence.",
                file=sys.stderr,
            )
            return False

vars_dict = {
    "DOMAIN": os.environ.get("DOMAIN"),
    "USER_ID": os.environ.get("USER_ID"),
    "GCP_ID": os.environ.get("GCP_ID"),
    "ENV_ID": os.environ.get("ENV_ID"),
    "INSTANCE": os.environ.get("FIREBASE_RTDB"),
    "STIM_STRENGTH": os.environ.get("STIM_STRENGTH"),
}
