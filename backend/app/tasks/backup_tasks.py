"""Celery tasks for device backups."""
from celery import current_task
from datetime import datetime, timedelta
import logging

from ..core.celery_config import celery_app
from ..core.database import SessionLocal
from ..models.device import Device
from ..models.backup import DeviceBackup, BackupSchedule, BackupStatus, BackupType, BackupMethod
from ..services.backup_service import backup_service
from ..services.alert_service import AlertService
from ..models.alert import AlertType, AlertSeverity

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def backup_device(
    self,
    device_id: int,
    backup_type: str = "running_config",
    backup_method: str = "ssh",
    created_by: str = "system",
):
    """
    Backup a single device configuration.

    Args:
        device_id: Device ID to backup
        backup_type: running_config, startup_config, or full
        backup_method: ssh, scp, tftp, sftp
        created_by: User who triggered the backup
    """
    db = SessionLocal()
    try:
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            return {"error": f"Device {device_id} not found"}

        # Map string to enum
        backup_type_enum = BackupType(backup_type)
        backup_method_enum = BackupMethod(backup_method)

        # Run backup
        backup = backup_service.run_backup(
            device=device,
            backup_type=backup_type_enum,
            backup_method=backup_method_enum,
            created_by=created_by,
        )

        db.add(backup)
        db.commit()
        db.refresh(backup)

        result = {
            "device_id": device_id,
            "device_name": device.name,
            "backup_id": backup.id,
            "status": backup.status.value,
            "file_path": backup.file_path,
            "file_size": backup.file_size,
        }

        # Create alert if backup failed
        if backup.status == BackupStatus.FAILED:
            alert_service = AlertService(db)
            alert_service.create_alert(
                alert_type=AlertType.BACKUP_FAILED,
                severity=AlertSeverity.WARNING,
                title=f"Backup Failed - {device.name}",
                message=f"Backup failed: {backup.error_message}",
                device=device,
            )

        return result

    except Exception as e:
        logger.error(f"Error backing up device {device_id}: {e}")
        db.rollback()
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(bind=True)
def run_scheduled_backups(self):
    """
    Run all scheduled backups.

    Called by Celery Beat based on schedule.
    """
    db = SessionLocal()
    try:
        # Get all enabled backup schedules
        schedules = (
            db.query(BackupSchedule)
            .filter(BackupSchedule.enabled == True)
            .all()
        )

        results = {
            "total_schedules": len(schedules),
            "backups_triggered": 0,
            "backups_failed": 0,
            "devices": [],
        }

        for schedule in schedules:
            # Determine devices to backup
            devices = []

            if schedule.device_id:
                device = db.query(Device).filter(Device.id == schedule.device_id).first()
                if device:
                    devices.append(device)
            elif schedule.group_id:
                # Backup all devices in group
                devices = (
                    db.query(Device)
                    .filter(Device.group_id == schedule.group_id)
                    .all()
                )
            else:
                # Backup all devices
                devices = db.query(Device).filter(Device.polling_enabled == True).all()

            for device in devices:
                try:
                    # Trigger backup task
                    backup_device.delay(
                        device_id=device.id,
                        backup_type=schedule.backup_type.value,
                        backup_method=schedule.backup_method.value,
                        created_by="scheduled",
                    )
                    results["backups_triggered"] += 1
                    results["devices"].append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "status": "triggered",
                    })
                except Exception as e:
                    logger.error(f"Error triggering backup for device {device.id}: {e}")
                    results["backups_failed"] += 1
                    results["devices"].append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "status": "failed",
                        "error": str(e),
                    })

        return results

    except Exception as e:
        logger.error(f"Error in run_scheduled_backups: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True)
def cleanup_old_backups(self, days_old: int = None):
    """
    Clean up old backups beyond retention period.

    Args:
        days_old: Delete backups older than this many days (default: from settings)
    """
    db = SessionLocal()
    try:
        from ..core.config import settings
        retention_days = days_old or settings.BACKUP_RETENTION_DAYS

        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Get old backups
        old_backups = (
            db.query(DeviceBackup)
            .filter(DeviceBackup.created_at < cutoff_date)
            .all()
        )

        deleted = 0
        for backup in old_backups:
            # Delete file
            if backup.file_path:
                try:
                    import os
                    if os.path.exists(backup.file_path):
                        os.unlink(backup.file_path)
                except Exception as e:
                    logger.error(f"Error deleting backup file {backup.file_path}: {e}")

            # Delete record
            db.delete(backup)
            deleted += 1

        db.commit()

        return {
            "deleted_count": deleted,
            "cutoff_date": cutoff_date.isoformat(),
            "retention_days": retention_days,
        }

    except Exception as e:
        logger.error(f"Error in cleanup_old_backups: {e}")
        db.rollback()
        raise self.retry(exc=e, countdown=300)
    finally:
        db.close()


@celery_app.task(bind=True)
def backup_all_devices(self, backup_type: str = "running_config"):
    """
    Backup all devices immediately.

    Used for ad-hoc bulk backup operations.
    """
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.polling_enabled == True).all()

        results = {
            "total_devices": len(devices),
            "backups_triggered": 0,
        }

        for device in devices:
            backup_device.delay(
                device_id=device.id,
                backup_type=backup_type,
                backup_method="ssh",
                created_by="bulk_operation",
            )
            results["backups_triggered"] += 1

        return results

    except Exception as e:
        logger.error(f"Error in backup_all_devices: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task
def cleanup_device_backups(device_id: int, retain_count: int = 30):
    """
    Clean up old backups for a specific device.

    Keeps only the most recent backups up to retain_count.
    """
    db = SessionLocal()
    try:
        deleted = backup_service.cleanup_old_backups(
            db.query(Device).filter(Device.id == device_id).first(),
            retain_count=retain_count,
        )
        return {"device_id": device_id, "deleted_count": deleted}
    except Exception as e:
        logger.error(f"Error cleaning up backups for device {device_id}: {e}")
        return {"device_id": device_id, "error": str(e)}
    finally:
        db.close()
