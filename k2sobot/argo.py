import subprocess
import logging
import os
from functools import wraps
import shared_state as shared

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
            logging.info("ArgoCD already authenticated")
            return True

        # Need to login
        logging.info(f"Logging into ArgoCD server: {ARGOCD_SERVER}")
        login_command = ["argocd", "login", ARGOCD_SERVER, "--username", ARGOCD_USERNAME, "--password", ARGOCD_PASSWORD, "--grpc-web", "--plaintext", "--skip-test-tls"]

        if ARGOCD_INSECURE:
            login_command.append("--insecure")

        login_result = subprocess.run(login_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)

        if login_result.returncode == 0:
            logging.info("ArgoCD login successful")
            return True
        else:
            logging.error(f"ArgoCD login failed: {login_result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logging.error("ArgoCD login timeout")
        return False
    except Exception as e:
        logging.error(f"ArgoCD login error: {str(e)}")
        return False

def require_argocd_auth(func):
    """Decorator to ensure ArgoCD authentication before function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not ensure_argocd_login():
            return "Error: Failed to authenticate with ArgoCD. Please check server connection and credentials."
        return func(*args, **kwargs)
    return wrapper


@require_argocd_auth
def get_argo_applications():
    try:
        command = ["argocd", "app", "list", "-o", "name"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        applications = [app.strip() for app in result.stdout.strip().split('\n') if app.strip()]
        return applications
    except subprocess.CalledProcessError as e:
        logging.error("Error running argocd command: %s", e)
        return []


@require_argocd_auth
def get_argo_application_status(channel_id, app_name):
    try:
        command = ["argocd", "app", "get", app_name]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout.strip()
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"```\n{output}\n```")
    except subprocess.CalledProcessError as e:
        logging.error("Error running argocd command: %s", e)
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"Error executing command:\n```\n{e.stderr}\n```")


@require_argocd_auth
def get_argo_application_revisions(channel_id, app_name):
    try:
        command = ["argocd", "app", "history", app_name]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout.strip()
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"```\n{output}\n```")
    except subprocess.CalledProcessError as e:
        logging.error("Error running argocd history command: %s", e)
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"Error executing command:\n```\n{e.stderr}\n```")


@require_argocd_auth
def get_argo_application_revisions_for_rollback(app_name):
    try:
        command = ["argocd", "app", "history", app_name, "-o", "id"]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        revisions = [rev.strip() for rev in result.stdout.strip().split('\n') if rev.strip()]
        return revisions
    except subprocess.CalledProcessError as e:
        logging.error("Error getting revisions for rollback: %s", e)
        return []


@require_argocd_auth
def rollback_argo_application(channel_id, app_name, revision):
    try:
        command = ["argocd", "app", "rollback", app_name, revision]
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

        # Extract key information from the output
        output = result.stdout.strip()
        lines = output.split('\n')

        # Find the summary section (usually starts with "Name:")
        summary_start = -1
        for i, line in enumerate(lines):
            if line.startswith('Name:'):
                summary_start = i
                break

        if summary_start != -1:
            # Get the summary section
            summary_lines = []
            for line in lines[summary_start:]:
                if line.startswith(('Name:', 'Project:', 'Sync Status:', 'Health Status:', 'Sync Revision:', 'Phase:', 'Duration:', 'Message:')):
                    summary_lines.append(line)
                elif line.startswith('GROUP') or not line.strip():
                    break

            summary = '\n'.join(summary_lines)
            shared.slack_client.chat_postMessage(
                channel=channel_id,
                text=f"✅ **Rollback completed for `{app_name}` to revision `{revision}`**\n```\n{summary}\n```"
            )
        else:
            # Fallback to a simple success message
            shared.slack_client.chat_postMessage(
                channel=channel_id,
                text=f"✅ **Rollback completed successfully**\nApplication: `{app_name}`\nRevision: `{revision}`"
            )

    except subprocess.CalledProcessError as e:
        logging.error("Error rolling back application: %s", e)
        error_message = e.stderr.strip()

        # Check for specific auto-sync error
        if "auto-sync is enabled" in error_message:
            shared.slack_client.chat_postMessage(
                channel=channel_id,
                text=f"⚠️ **Rollback blocked**: Auto-sync is enabled for `{app_name}`\n\n"
                     f"**Options to resolve:**\n"
                     f"• Disable auto-sync: `argocd app set {app_name} --sync-policy=none`\n"
                     f"• Use manual sync instead: `argocd app sync {app_name} --revision {revision}`\n"
                     f"• Or rollback via Git repository\n\n"
                     f"```\n{error_message}\n```"
            )
        else:
            shared.slack_client.chat_postMessage(channel=channel_id, text=f"❌ Rollback failed:\n```\n{error_message}\n```")


@require_argocd_auth
def run_argo_command(channel_id, command):
    try:
        logging.info("Running command: %s", command)
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"```\n{output}\n```")
    except subprocess.CalledProcessError as e:
        shared.slack_client.chat_postMessage(channel=channel_id, text=f"Error executing command:\n```\n{e.output}\n```")