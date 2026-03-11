"""
helm repo add kuberay https://ray-project.github.io/kuberay-helm/
helm repo update
helm install kuberay-operator
helm install raycluster kuberay/ray-_qfn_cluster_node --version 1.0.0
"""


def connect_cluster(cluster_name, zone):
    return f"""
    gcloud containerclusters get-credentials {cluster_name} --zone {zone}
    """


def install_kuberay():
    return f"""
    helm install kuberay-operator kuberay/kuberay-operator --version 1.0.0
    """


def get_pods():
    return f"""
    kubectl get pods
    """

def get_ray_cluster():
    return f"""
    kubectl get rayclusters
    """