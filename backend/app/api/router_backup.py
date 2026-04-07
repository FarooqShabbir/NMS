"""Device backup API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..core.task_dispatcher import dispatch_task
from ..models.device import Device, DeviceGroup
from ..models.backup import DeviceBackup, BackupSchedule, ConfigChange, BackupStatus, BackupType, BackupMethod
from ..schemas.backup import (
    DeviceBackupResponse,
    BackupListResponse,
    BackupScheduleCreate,
    BackupScheduleResponse,
    ConfigChangeResponse,
    BackupStatsResponse,
    DeviceBackupStatsResponse,
)
from ..tasks.backup_tasks import backup_device, backup_all_devices
from ..services.backup_service import backup_service

router = APIRouter(prefix="/api/backups", tags=["backups"])


# ============================================
# Device Backup Endpoints
# ============================================

@router.get("", response_model=List[BackupListResponse])
def list_backups(
    device_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    backup_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List device backups with optional filters."""
    query = db.query(DeviceBackup)

    if device_id:
        query = query.filter(DeviceBackup.device_id == device_id)
    if status:
        query = query.filter(DeviceBackup.status == status)
    if backup_type:
        query = query.filter(DeviceBackup.backup_type == backup_type)

    query = query.order_by(DeviceBackup.created_at.desc())

    backups = query.offset(skip).limit(limit).all()

    # Enrich with device info
    results = []
    for backup in backups:
        device = db.query(Device).filter(Device.id == backup.device_id).first()
        result = BackupListResponse(
            id=backup.id,
            device_id=backup.device_id,
            device_name=device.name if device else "Unknown",
            device_ip=str(device.ip_address) if device else "N/A",
            backup_name=backup.backup_name,
            backup_type=backup.backup_type,
            backup_method=backup.backup_method,
            status=backup.status,
            error_message=backup.error_message,
            file_path=backup.file_path,
            file_size=backup.file_size,
            git_commit_hash=backup.git_commit_hash,
            started_at=backup.started_at,
            completed_at=backup.completed_at,
            created_by=backup.created_by,
        )
        results.append(result)

    return results


@router.get("/{backup_id}", response_model=DeviceBackupResponse)
def get_backup(backup_id: int, db: Session = Depends(get_db)):
    """Get details of a specific backup."""
    backup = db.query(DeviceBackup).filter(DeviceBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")
    return backup


@router.post("/trigger")
def trigger_backup(
    device_id: int = Query(...),
    backup_type: str = Query("running_config", regex="^(running_config|startup_config|full)$"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Trigger an immediate backup of a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    task_id = dispatch_task(
        background_tasks,
        backup_device,
        device_id=device.id,
        backup_type=backup_type,
        backup_method="ssh",
        created_by="api",
    )

    return {
        "message": f"Backup triggered for device {device.name}",
        "task_id": task_id,
    }


@router.post("/trigger-all")
def trigger_all_backups(
    backup_type: str = Query("running_config", regex="^(running_config|startup_config|full)$"),
    background_tasks: BackgroundTasks = None,
):
    """Trigger backups for all devices."""
    task_id = dispatch_task(background_tasks, backup_all_devices, backup_type=backup_type)

    return {
        "message": "Backups triggered for all devices",
        "task_id": task_id,
    }


@router.get("/{backup_id}/download")
def download_backup(backup_id: int, db: Session = Depends(get_db)):
    """Download backup file."""
    backup = db.query(DeviceBackup).filter(DeviceBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if not backup.file_path:
        raise HTTPException(status_code=404, detail="Backup file not available")

    import os
    if not os.path.exists(backup.file_path):
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    return FileResponse(
        backup.file_path,
        media_type="text/plain",
        filename=backup.backup_name,
    )


@router.get("/{backup_id}/diff")
def get_backup_diff(
    backup_id: int,
    compare_with: int = Query(...),
    db: Session = Depends(get_db),
):
    """Compare two backups and show diff."""
    backup1 = db.query(DeviceBackup).filter(DeviceBackup.id == backup_id).first()
    backup2 = db.query(DeviceBackup).filter(DeviceBackup.id == compare_with).first()

    if not backup1 or not backup2:
        raise HTTPException(status_code=404, detail="One or both backups not found")

    diff = backup_service.get_backup_diff(backup1, backup2)
    return diff


@router.delete("/{backup_id}")
def delete_backup(backup_id: int, db: Session = Depends(get_db)):
    """Delete a backup."""
    backup = db.query(DeviceBackup).filter(DeviceBackup.id == backup_id).first()
    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    # Delete file
    if backup.file_path:
        import os
        if os.path.exists(backup.file_path):
            os.unlink(backup.file_path)

    db.delete(backup)
    db.commit()

    return {"message": "Backup deleted"}


# ============================================
# Backup Schedule Endpoints
# ============================================

@router.get("/schedules", response_model=List[BackupScheduleResponse])
def list_backup_schedules(db: Session = Depends(get_db)):
    """List all backup schedules."""
    schedules = db.query(BackupSchedule).all()

    results = []
    for schedule in schedules:
        device = None
        group = None
        if schedule.device_id:
            device = db.query(Device).filter(Device.id == schedule.device_id).first()
        if schedule.group_id:
            group = db.query(DeviceGroup).filter(DeviceGroup.id == schedule.group_id).first()

        results.append(
            BackupScheduleResponse(
                id=schedule.id,
                device_id=schedule.device_id,
                group_id=schedule.group_id,
                device_name=device.name if device else None,
                group_name=group.name if group else None,
                enabled=schedule.enabled,
                frequency=schedule.frequency,
                hour=schedule.hour,
                minute=schedule.minute,
                backup_type=schedule.backup_type,
                backup_method=schedule.backup_method,
                retain_count=schedule.retain_count,
                notify_on_success=schedule.notify_on_success,
                notify_on_failure=schedule.notify_on_failure,
                created_at=schedule.created_at,
            )
        )

    return results


@router.post("/schedules", response_model=BackupScheduleResponse, status_code=201)
def create_backup_schedule(
    schedule_data: BackupScheduleCreate,
    db: Session = Depends(get_db),
):
    """Create a new backup schedule."""
    schedule = BackupSchedule(
        device_id=schedule_data.device_id,
        group_id=schedule_data.group_id,
        enabled=schedule_data.enabled,
        frequency=schedule_data.frequency,
        hour=schedule_data.hour,
        minute=schedule_data.minute,
        backup_type=schedule_data.backup_type,
        backup_method=schedule_data.backup_method,
        retain_count=schedule_data.retain_count,
        notify_on_success=schedule_data.notify_on_success,
        notify_on_failure=schedule_data.notify_on_failure,
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return schedule


@router.put("/schedules/{schedule_id}", response_model=BackupScheduleResponse)
def update_backup_schedule(
    schedule_id: int,
    schedule_data: dict,
    db: Session = Depends(get_db),
):
    """Update a backup schedule."""
    schedule = db.query(BackupSchedule).filter(BackupSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for key, value in schedule_data.items():
        if hasattr(schedule, key):
            setattr(schedule, key, value)

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return schedule


@router.delete("/schedules/{schedule_id}")
def delete_backup_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """Delete a backup schedule."""
    schedule = db.query(BackupSchedule).filter(BackupSchedule.id == schedule_id).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    db.delete(schedule)
    db.commit()

    return {"message": "Schedule deleted"}


# ============================================
# Config Change Tracking
# ============================================

@router.get("/changes", response_model=List[ConfigChangeResponse])
def list_config_changes(
    device_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List configuration changes."""
    query = db.query(ConfigChange)

    if device_id:
        query = query.filter(ConfigChange.device_id == device_id)

    query = query.order_by(ConfigChange.change_detected_at.desc())

    changes = query.offset(skip).limit(limit).all()

    results = []
    for change in changes:
        device = db.query(Device).filter(Device.id == change.device_id).first()
        results.append(
            ConfigChangeResponse(
                id=change.id,
                device_id=change.device_id,
                device_name=device.name if device else "Unknown",
                change_type=change.change_type,
                diff_summary=change.diff_summary,
                detection_method=change.detection_method,
                change_detected_at=change.change_detected_at,
                created_at=change.created_at,
            )
        )

    return results


# ============================================
# Statistics
# ============================================

@router.get("/stats", response_model=BackupStatsResponse)
def get_backup_stats(db: Session = Depends(get_db)):
    """Get backup statistics."""
    total = db.query(DeviceBackup).count()
    successful = db.query(DeviceBackup).filter(DeviceBackup.status == BackupStatus.SUCCESS).count()
    failed = db.query(DeviceBackup).filter(DeviceBackup.status == BackupStatus.FAILED).count()
    in_progress = db.query(DeviceBackup).filter(DeviceBackup.status == BackupStatus.IN_PROGRESS).count()

    # Total size
    total_size = db.query(func.sum(DeviceBackup.file_size)).scalar() or 0

    # Last backup
    last_backup = (
        db.query(DeviceBackup)
        .filter(DeviceBackup.status == BackupStatus.SUCCESS)
        .order_by(DeviceBackup.completed_at.desc())
        .first()
    )

    return BackupStatsResponse(
        total_backups=total,
        successful_backups=successful,
        failed_backups=failed,
        pending_backups=in_progress,
        total_size_bytes=total_size,
        last_backup_at=last_backup.completed_at if last_backup else None,
        last_successful_backup_at=last_backup.completed_at if last_backup else None,
    )


@router.get("/stats/by-device", response_model=List[DeviceBackupStatsResponse])
def get_device_backup_stats(db: Session = Depends(get_db)):
    """Get backup statistics per device."""
    devices = db.query(Device).all()

    results = []
    for device in devices:
        backups = db.query(DeviceBackup).filter(DeviceBackup.device_id == device.id).all()
        last_backup = max((b for b in backups if b.completed_at), key=lambda b: b.completed_at, default=None)

        results.append(
            DeviceBackupStatsResponse(
                device_id=device.id,
                device_name=device.name,
                total_backups=len(backups),
                last_backup_at=last_backup.completed_at if last_backup else None,
                last_backup_status=last_backup.status if last_backup else None,
                config_changed_since_backup=False,  # Would need implementation
            )
        )

    return results
