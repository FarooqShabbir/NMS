"""Device backup SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class BackupMethod(str, enum.Enum):
    """Backup method enumeration."""
    SSH = "ssh"
    SCP = "scp"
    TFTP = "tftp"
    SFTP = "sftp"
    HTTP = "http"


class BackupStatus(str, enum.Enum):
    """Backup status enumeration."""
    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    SCHEDULED = "scheduled"


class BackupType(str, enum.Enum):
    """Backup type enumeration."""
    RUNNING_CONFIG = "running_config"
    STARTUP_CONFIG = "startup_config"
    FULL = "full"


class DeviceBackup(Base):
    """Device backup model."""
    __tablename__ = "device_backups"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # Backup identification
    backup_name = Column(String(255), nullable=False)
    backup_type = Column(SQLEnum(BackupType), default=BackupType.RUNNING_CONFIG)
    backup_method = Column(SQLEnum(BackupMethod), default=BackupMethod.SSH)

    # Status
    status = Column(SQLEnum(BackupStatus), default=BackupStatus.IN_PROGRESS)
    error_message = Column(Text, nullable=True)

    # File information
    file_path = Column(String(512), nullable=True)
    file_size = Column(BigInteger, default=0)  # bytes
    file_hash = Column(String(64), nullable=True)  # SHA256 hash

    # Version info (for Git)
    git_commit_hash = Column(String(40), nullable=True)
    git_branch = Column(String(255), nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    next_scheduled = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    created_by = Column(String(255), nullable=True)  # User who triggered backup
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="backups")


class BackupSchedule(Base):
    """Backup schedule configuration model."""
    __tablename__ = "backup_schedules"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)  # NULL = all devices
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=True)  # Or by group

    # Schedule
    enabled = Column(Boolean, default=True)
    frequency = Column(String(20), default="daily")  # hourly, daily, weekly, monthly, custom
    cron_expression = Column(String(100), nullable=True)  # Custom cron expression
    hour = Column(Integer, default=2)  # For daily
    minute = Column(Integer, default=0)
    day_of_week = Column(Integer, default=0)  # For weekly (0=Sunday)
    day_of_month = Column(Integer, default=1)  # For monthly

    # Backup settings
    backup_type = Column(SQLEnum(BackupType), default=BackupType.RUNNING_CONFIG)
    backup_method = Column(SQLEnum(BackupMethod), default=BackupMethod.SSH)
    retain_count = Column(Integer, default=30)  # Number of backups to retain

    # Notifications
    notify_on_success = Column(Boolean, default=False)
    notify_on_failure = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ConfigChange(Base):
    """Configuration change tracking model."""
    __tablename__ = "config_changes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    backup_id = Column(Integer, ForeignKey("device_backups.id"), nullable=True)

    # Change detection
    change_detected_at = Column(DateTime(timezone=True), server_default=func.now())
    change_type = Column(String(50), nullable=True)  # added, removed, modified

    # Diff storage
    diff_summary = Column(Text, nullable=True)  # Summary of changes
    diff_full = Column(Text, nullable=True)  # Full diff

    # Detection method
    detection_method = Column(String(50), nullable=True)  # syslog, polling, manual

    created_at = Column(DateTime(timezone=True), server_default=func.now())
