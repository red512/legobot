"""
ArgoCD tools - thin wrapper around argo.py
"""
import logging
import subprocess
import os
from functools import wraps
import argo

logger = logging.getLogger(__name__)

# ArgoCD connection configuration for minikube environment
ARGOCD_SERVER = os.getenv("ARGOCD_SERVER", "argocd-server.argo.svc.cluster.local:80")
ARGOCD_USERNAME = os.getenv("ARGOCD_USERNAME", "admin")
ARGOCD_PASSWORD = os.getenv("ARGOCD_PASSWORD", "BNoWRv-jt3UtMMaS")
ARGOCD_INSECURE = os.getenv("ARGOCD_INSECURE", "true").lower() == "true"

def ensure_argocd_login():
    """Ensure ArgoCD is logged in before executing commands"""
    try:
        # Check if already logged in
        check_command = ["argocd", "account", "get-user-info"]
        result = subprocess.run(check_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)

        if result.returncode == 0 and "Logged In: true" in result.stdout:
            logger.info("ArgoCD already authenticated")
            return True

        # Need to login
        logger.info(f"Logging into ArgoCD server: {ARGOCD_SERVER}")
        login_command = ["argocd", "login", ARGOCD_SERVER, "--username", ARGOCD_USERNAME, "--password", ARGOCD_PASSWORD, "--grpc-web", "--plaintext", "--skip-test-tls"]

        if ARGOCD_INSECURE:
            login_command.append("--insecure")

        login_result = subprocess.run(login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)

        if login_result.returncode == 0:
            logger.info("ArgoCD login successful")
            return True
        else:
            logger.error(f"ArgoCD login failed: {login_result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("ArgoCD login timeout")
        return False
    except Exception as e:
        logger.error(f"ArgoCD login error: {str(e)}")
        return False

def require_argocd_auth(func):
    """Decorator to ensure ArgoCD authentication before function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not ensure_argocd_login():
            return "Error: Failed to authenticate with ArgoCD. Please check server connection and credentials."
        return func(*args, **kwargs)
    return wrapper


def get_applications():
    """Get all ArgoCD applications"""
    return argo.get_argo_applications()


def get_application_revisions(app_name):
    """Get available revisions for rollback"""
    return argo.get_argo_application_revisions_for_rollback(app_name)


@require_argocd_auth
def get_application_status(app_name):
    """Get ArgoCD application status"""
    try:
        command = ["argocd", "app", "get", app_name]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=15)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Timeout getting application status"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


@require_argocd_auth
def get_application_history(app_name):
    """Get ArgoCD application revision history"""
    try:
        command = ["argocd", "app", "history", app_name]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=15)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Timeout getting application history"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"


@require_argocd_auth
def sync_application(app_name, revision=None):
    """Sync ArgoCD application with optional revision"""
    try:
        command = ["argocd", "app", "sync", app_name]
        if revision:
            command.extend(["--revision", revision])
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, timeout=30)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Error: Timeout syncing application"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"