ENDPOINT="https://container.googleapis.com/v1/projects/aixr-401704/locations/us-central1/clusters"


def get_cluster_data(
    name="bestbrain",
):
    return rf"""
{{
  "cluster": {{
    "name": {name},
    "network": "projects/aixr-401704/global/networks/default",
    "subnetwork": "projects/aixr-401704/regions/us-central1/subnetworks/default",
    "networkPolicy": {{}},
    "ipAllocationPolicy": {{
      "useIpAliases": true,
      "clusterIpv4CidrBlock": "/17",
      "stackType": "IPV4"
    }},
    "binaryAuthorization": {{
      "evaluationMode": "DISABLED"
    }},
    "autoscaling": {{
      "enableNodeAutoprovisioning": true,
      "autoprovisioningNodePoolDefaults": {{}}
    }},
    "networkConfig": {{
      "enableIntraNodeVisibility": true,
      "datapathProvider": "ADVANCED_DATAPATH",
      "defaultEnablePrivateNodes": false
    }},
    "authenticatorGroupsConfig": {{}},
    "databaseEncryption": {{
      "state": "DECRYPTED"
    }},
    "verticalPodAutoscaling": {{
      "enabled": true
    }},
    "releaseChannel": {{
      "channel": "REGULAR"
    }},
    "notificationConfig": {{
      "pubsub": {{}}
    }},
    "initialClusterVersion": "1.32.4-gke.1236007",
    "location": "us-central1",
    "autopilot": {{
      "enabled": true
    }},
    "loggingConfig": {{
      "componentConfig": {{
        "enableComponents": [
          "SYSTEM_COMPONENTS",
          "WORKLOADS"
        ]
      }}
    }},
    "monitoringConfig": {{
      "componentConfig": {{
        "enableComponents": [
          "SYSTEM_COMPONENTS",
          "STORAGE",
          "POD",
          "DEPLOYMENT",
          "STATEFULSET",
          "DAEMONSET",
          "HPA",
          "JOBSET",
          "CADVISOR",
          "KUBELET",
          "DCGM"
        ]
      }},
      "managedPrometheusConfig": {{
        "enabled": true,
        "autoMonitoringConfig": {{
          "scope": "NONE"
        }}
      }}
    }},
    "nodePoolAutoConfig": {{
      "resourceManagerTags": {{}}
    }},
    "fleet": {{
      "project": "aixr-401704"
    }},
    "securityPostureConfig": {{
      "mode": "BASIC",
      "vulnerabilityMode": "VULNERABILITY_DISABLED"
    }},
    "controlPlaneEndpointsConfig": {{
      "dnsEndpointConfig": {{
        "allowExternalTraffic": true
      }},
      "ipEndpointsConfig": {{
        "enabled": true,
        "enablePublicEndpoint": true,
        "globalAccess": false,
        "authorizedNetworksConfig": {{}}
      }}
    }},
    "enterpriseConfig": {{
      "desiredTier": "STANDARD"
    }},
    "secretManagerConfig": {{
      "enabled": false
    }}
  }}
}}


"""