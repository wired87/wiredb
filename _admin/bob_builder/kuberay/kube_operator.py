import subprocess
from typing import Tuple



class KubeRayWorkflowManager:
    """
    Manages the lifecycle of a KubeRay cluster on Kubernetes (GKE),
    encapsulating all kubectl and helm commands into stateful methods.
    """

    def __init__(self, cluster_name: str = "raycluster-kuberay", helm_version: str = "1.4.2"):
        self.CLUSTER_NAME = cluster_name
        self.HELM_VERSION = helm_version
        self.HEAD_POD_NAME = ""

    def _execute_command(self, command: str, run_default: bool = True, background: bool = False) -> Tuple[bool, str]:
        """
        Executes a shell command.
        """
        if not run_default:
            return True, f"Command skipped: {command}"

        try:
            # Determine how to run the command (background for port-forwarding)
            if background:
                process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Command started in background (PID: {process.pid})"
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                return True, result.stdout.strip()

        except subprocess.CalledProcessError as e:
            return False, f"ERROR: Command failed with code {e.returncode}.\nStderr: {e.stderr.strip()}"
        except FileNotFoundError:
            return False, "ERROR: Required tool (kubectl or helm) not found."

    # ----------------------------------------------------------------------
    # STEP 3: CLUSTER DEPLOYMENT
    # ----------------------------------------------------------------------
    def deploy_ray_cluster_cr(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Deploys the RayCluster Custom Resource via Helm.
        """
        command = f"helm install {self.CLUSTER_NAME} kuberay/ray-cluster --version {self.HELM_VERSION}"
        return self._execute_command(command, run_default)

    def view_ray_clusters(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Checks the status of deployed RayClusters.
        """
        command = "kubectl get rayclusters"
        return self._execute_command(command, run_default)

    def view_ray_pods(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Views the pods associated with the deployed RayCluster.
        """
        command = f"kubectl get pods --selector=ray.io/cluster={self.CLUSTER_NAME}"
        return self._execute_command(command, run_default)

    # ----------------------------------------------------------------------
    # STEP 4: APPLICATION RUN (Method 1 & 2 Abstraction)
    # ----------------------------------------------------------------------
    def get_head_pod_name(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Identifies and saves the name of the Ray Head Pod.
        """
        command = "kubectl get pods --selector=ray.io/node-type=head -o custom-columns=POD:metadata.name --no-headers"
        success, output = self._execute_command(command, run_default)
        if success:
            self.HEAD_POD_NAME = output
        return success, self.HEAD_POD_NAME

    def run_check_resources_exec(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Method 1: Executes a Ray command directly in the Head Pod.
        """
        if not self.HEAD_POD_NAME:
            return False, "ERROR: Head Pod name not set. Run get_head_pod_name first."

        command = f'kubectl exec -it {self.HEAD_POD_NAME} -- python -c "import ray; ray.init(); print(ray.cluster_resources())"'
        return self._execute_command(command, run_default)

    def setup_port_forwarding(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Sets up port-forwarding for job submission (Method 2).
        Runs in the background.
        """
        service_name = f"{self.CLUSTER_NAME}-head-svc"
        command = f"kubectl port-forward service/{service_name} 8265:8265 > /dev/null &"
        return self._execute_command(command, run_default, background=True)

    def submit_job_sdk(self, script_code: str, run_default: bool = True) -> Tuple[bool, str]:
        """
        Method 2: Submits a job to the cluster using the Ray Job SDK via port-forward.
        """
        # Note: The script code must be correctly escaped for the shell command.
        command = f'ray job submit --address http://localhost:8265 -- python -c "{script_code}"'
        return self._execute_command(command, run_default)

    # ----------------------------------------------------------------------
    # STEP 6: CLEANUP
    # ----------------------------------------------------------------------
    def cleanup_port_forward(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Kills the kubectl port-forward background process.
        """
        command = "killall kubectl"
        return self._execute_command(command, run_default)

    def delete_ray_cluster(self, run_default: bool = True) -> Tuple[bool, str]:
        """
        Deletes the RayCluster resource.
        """
        # Helm uninstall removes the resources created by the Helm chart.
        command = f"helm uninstall {self.CLUSTER_NAME}"
        return self._execute_command(command, run_default)

    def delete_kind_cluster(self, run_default: bool = False) -> Tuple[bool, str]:
        """
        Deletes the entire Kind cluster (if used for local testing).
        This command defaults to False as it's destructive and context-dependent.
        """
        command = "kind delete cluster"
        return self._execute_command(command, run_default)
