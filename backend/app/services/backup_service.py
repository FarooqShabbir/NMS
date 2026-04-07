"""Device backup service - SSH/SCP/TFTP backup with Git integration."""
import os
import subprocess
import tempfile
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import paramiko
from scp import SCPClient
import git

from ..core.config import settings
from ..models.device import Device
from ..models.backup import DeviceBackup, BackupStatus, BackupType, BackupMethod
from ..utils.helpers import calculate_hash, mask_sensitive_data


class BackupError(Exception):
    """Backup operation error."""
    pass


class BackupService:
    """Service for device configuration backup."""

    def __init__(self):
        self.backup_dir = Path(settings.BACKUP_DIR)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = 30  # SSH timeout seconds
        self.git_repo = None

        if settings.BACKUP_GIT_ENABLED and settings.BACKUP_GIT_REPO:
            self._init_git_repo()

    def _init_git_repo(self):
        """Initialize or open Git repository for backups."""
        try:
            if os.path.exists(settings.BACKUP_GIT_REPO):
                self.git_repo = git.Repo(settings.BACKUP_GIT_REPO)
            else:
                os.makedirs(settings.BACKUP_GIT_REPO, exist_ok=True)
                self.git_repo = git.Repo.init(settings.BACKUP_GIT_REPO)
        except Exception as e:
            self.git_repo = None

    def _get_ssh_client(self, device: Device) -> paramiko.SSHClient:
        """Create SSH client for device."""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Determine authentication method
        if device.ssh_key:
            # Use SSH key
            key_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
            key_file.write(device.ssh_key)
            key_file.close()

            try:
                key = paramiko.RSAKey.from_private_key_file(key_file.name)
                client.connect(
                    str(device.ip_address),
                    port=device.ssh_port or 22,
                    username=device.ssh_username,
                    pkey=key,
                    timeout=self.timeout,
                )
            finally:
                os.unlink(key_file.name)
        elif device.ssh_password:
            # Use password
            client.connect(
                str(device.ip_address),
                port=device.ssh_port or 22,
                username=device.ssh_username,
                password=device.ssh_password,
                timeout=self.timeout,
            )
        else:
            raise BackupError("No SSH credentials configured for device")

        return client

    def backup_ssh(self, device: Device, backup_type: BackupType = BackupType.RUNNING_CONFIG) -> Tuple[bool, str, str]:
        """
        Backup device configuration via SSH (screen scraping).

        Returns tuple of (success, config_content, error_message).
        """
        config_content = ""
        error_message = ""

        try:
            client = self._get_ssh_client(device)
            stdin, stdout, stderr = client.exec_command("terminal length 0")
            stdout.channel.recv_exit_status()

            # Determine command based on backup type and device OS
            if backup_type == BackupType.RUNNING_CONFIG:
                # Try Cisco IOS first
                stdin, stdout, stderr = client.exec_command("show running-config")
            else:
                stdin, stdout, stderr = client.exec_command("show startup-config")

            # Read output with timeout
            config_lines = []
            while True:
                line = stdout.readline()
                if not line:
                    break
                config_lines.append(line)

            config_content = "".join(config_lines)

            # Check for errors
            stderr_output = stderr.read().decode('utf-8', errors='ignore')
            if stderr_output and not config_content.strip():
                error_message = stderr_output

            client.close()

            # Validate config was retrieved
            if not config_content.strip():
                error_message = "Empty configuration received"
            elif "Invalid command" in config_content or "Error" in config_content:
                # Try alternative commands for different vendors
                error_message = "Command not recognized, device may use different CLI"

        except paramiko.AuthenticationException:
            error_message = "SSH authentication failed"
        except paramiko.SSHException as e:
            error_message = f"SSH error: {str(e)}"
        except Exception as e:
            error_message = f"Backup failed: {str(e)}"

        success = bool(config_content.strip()) and not error_message
        return success, config_content, error_message

    def backup_scp(self, device: Device, remote_path: str) -> Tuple[bool, str, str]:
        """
        Backup device configuration via SCP.

        Returns tuple of (success, config_content, error_message).
        """
        config_content = ""
        error_message = ""

        try:
            client = self._get_ssh_client(device)
            scp = SCPClient(client.get_transport())

            # Create temp file for SCP download
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                tmp_path = tmp_file.name

            try:
                scp.get(remote_path, tmp_path)
                with open(tmp_path, 'r') as f:
                    config_content = f.read()
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                scp.close()
                client.close()

        except Exception as e:
            error_message = f"SCP backup failed: {str(e)}"

        success = bool(config_content.strip()) and not error_message
        return success, config_content, error_message

    def backup_tftp(self, device: Device, tftp_server: str, remote_path: str) -> Tuple[bool, str]:
        """
        Trigger device to send backup via TFTP.

        This sends commands to the device to push config to TFTP server.
        Returns tuple of (success, error_message).
        """
        error_message = ""

        try:
            client = self._get_ssh_client(device)

            # Send TFTP command (Cisco IOS style)
            commands = [
                f"copy running-config tftp://{tftp_server}/{remote_path}",
            ]

            for cmd in commands:
                stdin, stdout, stderr = client.exec_command(cmd)
                # Some devices may need confirmation
                stdout.channel.recv_exit_status()

            client.close()

        except Exception as e:
            error_message = f"TFTP backup failed: {str(e)}"

        success = not error_message
        return success, error_message

    def save_backup(
        self,
        device: Device,
        config_content: str,
        backup_type: BackupType,
        backup_method: BackupMethod,
        created_by: Optional[str] = None,
    ) -> DeviceBackup:
        """
        Save backup to disk and database.

        Returns DeviceBackup record.
        """
        # Generate filename
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in device.name)
        filename = f"{safe_name}_{backup_type.value}_{timestamp}.cfg"

        # Create device-specific directory
        device_dir = self.backup_dir / str(device.id)
        device_dir.mkdir(parents=True, exist_ok=True)

        file_path = device_dir / filename

        # Write config to file
        with open(file_path, 'w') as f:
            f.write(config_content)

        # Calculate file hash
        file_hash = calculate_hash(config_content)

        # Get file size
        file_size = file_path.stat().st_size

        # Commit to Git if enabled
        git_commit = None
        git_branch = None
        if self.git_repo:
            try:
                # Copy file to git repo
                git_path = Path(settings.BACKUP_GIT_REPO) / filename
                with open(git_path, 'w') as f:
                    f.write(config_content)

                # Commit
                self.git_repo.index.add([str(git_path)])
                commit = self.git_repo.index.commit(
                    f"Backup: {device.name} ({device.ip_address}) - {backup_type.value}"
                )
                git_commit = commit.hexsha
                git_branch = self.git_repo.active_branch.name
            except Exception:
                pass  # Git failure shouldn't fail the backup

        # Create database record
        backup = DeviceBackup(
            device_id=device.id,
            backup_name=filename,
            backup_type=backup_type,
            backup_method=backup_method,
            status=BackupStatus.SUCCESS,
            file_path=str(file_path),
            file_size=file_size,
            file_hash=file_hash,
            git_commit_hash=git_commit,
            git_branch=git_branch,
            completed_at=datetime.utcnow(),
            created_by=created_by,
        )

        return backup

    def mark_backup_failed(
        self,
        device: Device,
        backup_type: BackupType,
        backup_method: BackupMethod,
        error_message: str,
        created_by: Optional[str] = None,
    ) -> DeviceBackup:
        """Create a failed backup record."""
        backup = DeviceBackup(
            device_id=device.id,
            backup_name=f"failed_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            backup_type=backup_type,
            backup_method=backup_method,
            status=BackupStatus.FAILED,
            error_message=error_message,
            completed_at=datetime.utcnow(),
            created_by=created_by,
        )
        return backup

    def run_backup(
        self,
        device: Device,
        backup_type: BackupType = BackupType.RUNNING_CONFIG,
        backup_method: BackupMethod = BackupMethod.SSH,
        created_by: Optional[str] = None,
    ) -> DeviceBackup:
        """
        Run a complete backup operation.

        Returns DeviceBackup record.
        """
        if backup_method == BackupMethod.SSH:
            success, config_content, error_message = self.backup_ssh(device, backup_type)

            if success and config_content:
                # Mask sensitive data before saving
                masked_config = mask_sensitive_data(config_content)
                return self.save_backup(
                    device, masked_config, backup_type, backup_method, created_by
                )
            else:
                return self.mark_backup_failed(
                    device, backup_type, backup_method, error_message, created_by
                )

        elif backup_method == BackupMethod.SCP:
            # Default remote path for Cisco devices
            remote_path = "running-config" if backup_type == BackupType.RUNNING_CONFIG else "startup-config"
            success, config_content, error_message = self.backup_scp(device, remote_path)

            if success and config_content:
                masked_config = mask_sensitive_data(config_content)
                return self.save_backup(
                    device, masked_config, backup_type, backup_method, created_by
                )
            else:
                return self.mark_backup_failed(
                    device, backup_type, backup_method, error_message, created_by
                )

        elif backup_method == BackupMethod.TFTP:
            # TFTP requires external server
            success, error_message = self.backup_tftp(
                device,
                tftp_server="127.0.0.1",  # Would need actual TFTP server
                remote_path=f"{device.id}_config.cfg",
            )

            if success:
                # TFTP would need to retrieve file from server
                return self.mark_backup_failed(
                    device, backup_type, backup_method,
                    "TFTP backup requires server implementation",
                    created_by,
                )
            else:
                return self.mark_backup_failed(
                    device, backup_type, backup_method, error_message, created_by
                )

        else:
            return self.mark_backup_failed(
                device, backup_type, backup_method,
                f"Unsupported backup method: {backup_method}",
                created_by,
            )

    def get_backup_diff(self, backup1: DeviceBackup, backup2: DeviceBackup) -> Dict[str, Any]:
        """
        Compare two backups and return diff.

        Returns dict with added, removed lines.
        """
        from ..utils.helpers import diff_configs

        if not backup1.file_path or not backup2.file_path:
            return {"error": "Backup files not available"}

        try:
            with open(backup1.file_path, 'r') as f:
                config1 = f.read()
            with open(backup2.file_path, 'r') as f:
                config2 = f.read()

            return diff_configs(config1, config2)
        except Exception as e:
            return {"error": str(e)}

    def restore_backup(
        self,
        backup: DeviceBackup,
        device: Device,
    ) -> Tuple[bool, str]:
        """
        Restore configuration from backup to device.

        Returns tuple of (success, error_message).
        """
        if not backup.file_path or not os.path.exists(backup.file_path):
            return False, "Backup file not found"

        try:
            client = self._get_ssh_client(device)

            with open(backup.file_path, 'r') as f:
                config = f.read()

            # Enter config mode and apply config
            # This is a simplified approach - production would need more careful handling
            stdin, stdout, stderr = client.exec_command("configure terminal")

            for line in config.splitlines():
                if line.strip() and not line.startswith('!'):
                    stdin.write(line + '\n')

            stdin.write('end\n')
            stdin.write('write memory\n')
            stdin.write('exit\n')

            stdout.channel.recv_exit_status()
            client.close()

            return True, ""

        except Exception as e:
            return False, f"Restore failed: {str(e)}"

    def cleanup_old_backups(self, device: Device, retain_count: int = 30) -> int:
        """
        Delete old backups beyond retention count.

        Returns number of deleted backups.
        """
        from sqlalchemy.orm import Session
        from ..core.database import SessionLocal
        from ..models.backup import DeviceBackup

        db = SessionLocal()
        try:
            # Get backups ordered by date
            backups = (
                db.query(DeviceBackup)
                .filter(DeviceBackup.device_id == device.id)
                .order_by(DeviceBackup.created_at.desc())
                .all()
            )

            deleted = 0
            for backup in backups[retain_count:]:
                # Delete file
                if backup.file_path and os.path.exists(backup.file_path):
                    os.unlink(backup.file_path)

                # Delete record
                db.delete(backup)
                deleted += 1

            db.commit()
            return deleted

        finally:
            db.close()


# Singleton instance
backup_service = BackupService()
