import os

import networkx as nx
from collections import defaultdict
import yaml



class KubeRayClusterCfgGenerator:
    def __init__(self, graph: nx.Graph, env, user_id, file_store, ray_version="2.9.0"):
        self.graph = graph
        self.env = env
        self.user_id = user_id

        self.node_counts = defaultdict(int)
        self.ray_version = ray_version
        self.cluster_yaml = None
        self.file_store=file_store

    def main(self):
        self._count_node_types()

        self.generate_cluster_yaml(
            manager_image="myregistry/manager",
            worker_image="myregistry/worker",
            img_tag="latest"
        )

    def _count_node_types(self):
        for _, data in self.graph.nodes(data=True):
            node_type = data.get('type')
            if not node_type:
                raise ValueError("Each node must have a 'type'")
            if node_type not in self.node_counts:
                self.node_counts[node_type] = 0
            self.node_counts[node_type] += 1


    def _create_head_spec(self, manager_image, img_tag="latest"):
        """
        server
        cluster_utils
        (manager)
        """
        return {
            "serviceType": "ClusterIP",
            "rayStartParams": {
                "dashboard-host": "0.0.0.0"
            },
            "template": {
                "spec": {
                    "container": [
                        {
                            "name": "ray-head",
                            "image": f"{manager_image}:{img_tag}",
                            "env": [
                                {
                                    "name": "SERVER_ACCESS_KEY",  # todo more robust (keypair) -> switch @ each req
                                    "value": self.env["id"],
                                },
                                {
                                    "name": "ENV_ID",
                                    "value": self.env["id"],
                                },
                                {
                                    "name": "USER_ID",
                                    "value": self.user_id,
                                },
                                {
                                    "name": "FIREBASE_RTDB",
                                    "value": os.environ.get("FIREBASE_RTDB"),
                                },
                            ],

                            "resources": {
                                "limits": {
                                    "cpu": "200m",
                                    "memory": "256Mi"
                                }
                            },
                            "command": [
                                "ray",
                                "start",
                                "--head",
                                "--port=6379",
                                "--dashboard-host=0.0.0.0"
                            ]
                        }
                    ]
                }
            }
        }



    def _create_worker_group_spec(self, node_type, count, worker_image, manager_image, img_tag="latest"):
        """
        Create a worker group spec with multiple container per pod.
        `worker_images` should be a list of image names.
        """
        containers = []

        containers.append({
            "name": "manager",
            "image": f"{manager_image}:{img_tag}",
            "resources": {
                "limits": {
                    "cpu": "200m",
                    "memory": "256Mi"
                }
            },
            "command": [
                "ray",
                "start",
                "--address=ray-head:6379"
            ]
        })

        # Worker-Container (mehrere pro Pod)
        for i in range(count):
            containers.append({
                "name": f"worker-{i}",
                "image": f"{worker_image}:{img_tag}",
                "resources": {
                    "limits": {
                        "cpu": "100m",
                        "memory": "128Mi"
                    }
                },
                "command": [
                    "ray",
                    "start",
                    "--address=ray-head:6379"
                ]
            })

        return {
            "groupName": node_type,
            "replicas": 1,
            "rayStartParams": {},
            "template": {
                "spec": {
                    "container": containers
                }
            }
        }
    #def _manager_image(self):

    def generate_cluster_yaml(self, manager_image, worker_image, img_tag="latest"):
        cluster = {
            "apiVersion": "ray.io/v1",
            "kind": "RayCluster",
            "metadata": {
                "name": "ray-cluster"
            },
            "spec": {
                "rayVersion": self.ray_version,
                "headGroupSpec": self._create_head_spec(manager_image, img_tag),
                "workerGroupSpecs": []
            }
        }

        for node_type, count in self.node_counts.items():
            cluster["spec"]["workerGroupSpecs"].append(
                self._create_worker_group_spec( node_type, count, worker_image, manager_image)
            )

        self.cluster_yaml = yaml.dump(cluster, sort_keys=False)

        self.save_to_file_store()


    def get_yaml(self):
        return self.cluster_yaml

    def get_yaml_content(self):
        save_path = os.path.join(
            self.file_store.name,
            "ray_cfg.yaml",
        )
        return self.get_yaml(), save_path

