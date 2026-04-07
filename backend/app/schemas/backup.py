"""Pydantic schemas for backup endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BackupMethod(str, Enum):
    SSH = "ssh"
    SCP = "scp"
    TFTP = "tftp"
    SFTP = "sftp"
    HTTP = "http"


class BackupStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    SCHEDULED = "scheduled"


class BackupType(str, Enum):
    RUNNING_CONFIG = "running_config"
    STARTUP_CONFIG = "startup_config"
    FULL = "full"


# Device Backup Schemas
class DeviceBackupBase(BaseModel):
    backup_name: str = Field(..., min_length=1, max_length=255)
    backup_type: BackupType = BackupType.RUNNING_CONFIG
    backup_method: BackupMethod = BackupMethod.SSH
    notes: Optional[str] = None


class DeviceBackupCreate(DeviceBackupBase):
    device_id: int


class DeviceBackupResponse(DeviceBackupBase):
    id: int
    device_id: int
    status: BackupStatus
    error_message: Optional[str] = None
    file_path: Optional[str] = None
    file_size: int = 0
    git_commit_hash: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None

    class Config:
        from_attributes = True


class BackupListResponse(DeviceBackupResponse):
    device_name: str
    device_ip: str


# Backup Schedule Schemas
class BackupScheduleBase(BaseModel):
    enabled: bool = True
    frequency: str = "daily"  # hourly, daily, weekly, monthly, custom
    cron_expression: Optional[str] = None
    hour: int = Field(default=2, ge=0, le=23)
    minute: int = Field(default=0, ge=0, le=59)
    day_of_week: int = Field(default=0, ge=0, le=6)
    day_of_month: int = Field(default=1, ge=1, le=31)
    backup_type: BackupType = BackupType.RUNNING_CONFIG
    backup_method: BackupMethod = BackupMethod.SSH
    retain_count: int = Field(default=30, ge=1, le=365)
    notify_on_success: bool = False
    notify_on_failure: bool = True


class BackupScheduleCreate(BackupScheduleBase):
    device_id: Optional[int] = None
    group_id: Optional[int] = None


class BackupScheduleResponse(BackupScheduleBase):
    id: int
    device_id: Optional[int] = None
    group_id: Optional[int] = None
    device_name: Optional[str] = None
    group_name: Optional[str] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Config Change Schema
class ConfigChangeResponse(BaseModel):
    id: int
    device_id: int
    device_name: str
    change_type: Optional[str] = None
    diff_summary: Optional[str] = None
    detection_method: Optional[str] = None
    change_detected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Backup Statistics
class BackupStatsResponse(BaseModel):
    total_backups: int = 0
    successful_backups: int = 0
    failed_backups: int = 0
    pending_backups: int = 0
    total_size_bytes: int = 0
    last_backup_at: Optional[datetime] = None
    last_successful_backup_at: Optional[datetime] = None


class DeviceBackupStatsResponse(BaseModel):
    device_id: int
    device_name: str
    total_backups: int = 0
    last_backup_at: Optional[datetime] = None
    last_backup_status: Optional[BackupStatus] = None
    config_changed_since_backup: bool = False
