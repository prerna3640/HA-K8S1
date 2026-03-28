"""
scaler.py
---------
Kubernetes scaling operations using the official Python client.
Handles both in-cluster (pod) and out-of-cluster (local kubeconfig) auth.
"""

import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesScaler:
    """Reads and patches the replica count of a Kubernetes Deployment."""

    def __init__(self, namespace: str, deployment_name: str):
        self.namespace = namespace
        self.deployment_name = deployment_name
        self._init_client()

    def _init_client(self) -> None:
        try:
            config.load_incluster_config()
            logger.info("Kubernetes auth: in-cluster config")
        except config.ConfigException:
            config.load_kube_config()
            logger.info("Kubernetes auth: local kubeconfig")
        self._apps = client.AppsV1Api()

    # ── read ──────────────────────────────────────────────────────────────────

    def get_current_replicas(self) -> int | None:
        """Return the current spec.replicas of the deployment, or None on error."""
        try:
            deploy = self._apps.read_namespaced_deployment(
                name=self.deployment_name,
                namespace=self.namespace,
            )
            return deploy.spec.replicas
        except ApiException as exc:
            logger.error(
                f"Failed to read deployment {self.namespace}/{self.deployment_name}: {exc}"
            )
            return None

    # ── write ─────────────────────────────────────────────────────────────────

    def scale(self, replicas: int) -> bool:
        """
        Patch the deployment replica count.
        Returns True on success, False on failure.
        """
        try:
            body = {"spec": {"replicas": replicas}}
            self._apps.patch_namespaced_deployment_scale(
                name=self.deployment_name,
                namespace=self.namespace,
                body=body,
            )
            logger.info(
                f"Scaled {self.namespace}/{self.deployment_name} → {replicas} replicas"
            )
            return True
        except ApiException as exc:
            logger.error(
                f"Failed to scale {self.namespace}/{self.deployment_name}: {exc}"
            )
            return False
