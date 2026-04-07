"""Alert SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Text, Float as SQLFloat
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class AlertSeverity(str, enum.Enum):
    """Alert severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, enum.Enum):
    """Alert status enumeration."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertType(str, enum.Enum):
    """Alert type enumeration."""
    DEVICE_DOWN = "device_down"
    DEVICE_UP = "device_up"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    HIGH_BANDWIDTH = "high_bandwidth"
    INTERFACE_DOWN = "interface_down"
    INTERFACE_ERROR = "interface_error"
    BGP_DOWN = "bgp_down"
    BGP_FLAP = "bgp_flap"
    OSPF_DOWN = "ospf_down"
    EIGRP_DOWN = "eigrp_down"
    VPN_DOWN = "vpn_down"
    BACKUP_FAILED = "backup_failed"
    CONFIG_CHANGED = "config_changed"
    CUSTOM = "custom"


class Alert(Base):
    """Alert model."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    interface_id = Column(Integer, ForeignKey("interfaces.id"), nullable=True)

    # Alert identification
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), nullable=False)
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)

    # Alert content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)  # JSON string with additional info

    # Threshold info
    threshold_value = Column(SQLFloat, nullable=True)
    current_value = Column(SQLFloat, nullable=True)
    threshold_unit = Column(String(50), nullable=True)

    # Timing
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)

    # Acknowledgment
    acknowledged_by = Column(String(255), nullable=True)
    acknowledgment_note = Column(Text, nullable=True)

    # Notification tracking
    notification_count = Column(Integer, default=0)
    notifications_sent = Column(Text, nullable=True)  # JSON list of channels

    # Suppression
    suppressed = Column(Boolean, default=False)
    suppression_reason = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="alerts")


class AlertRule(Base):
    """Alert rule configuration model."""
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, index=True)

    # Rule identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)

    # Rule configuration
    alert_type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.WARNING)

    # Threshold configuration
    metric = Column(String(100), nullable=True)  # cpu_usage, memory_usage, etc.
    operator = Column(String(10), nullable=True)  # gt, lt, eq, ne
    threshold_value = Column(SQLFloat, nullable=True)
    duration_seconds = Column(Integer, default=0)  # How long condition must persist

    # Scope
    device_ids = Column(Text, nullable=True)  # JSON list, NULL = all devices
    group_ids = Column(Text, nullable=True)  # JSON list

    # Notification settings
    notify_email = Column(Boolean, default=False)
    notify_slack = Column(Boolean, default=False)
    notify_telegram = Column(Boolean, default=False)
    notify_webhook = Column(Boolean, default=False)
    webhook_url = Column(String(512), nullable=True)

    # Escalation
    escalate_after_minutes = Column(Integer, nullable=True)
    escalate_severity = Column(SQLEnum(AlertSeverity), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MaintenanceWindow(Base):
    """Maintenance window for suppressing alerts."""
    __tablename__ = "maintenance_windows"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Schedule
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(100), nullable=True)  # iCal RRULE format

    # Scope
    device_ids = Column(Text, nullable=True)  # JSON list
    alert_types = Column(Text, nullable=True)  # JSON list

    # Settings
    suppress_notifications = Column(Boolean, default=True)
    suppress_alert_creation = Column(Boolean, default=False)

    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SyslogMessage(Base):
    """Syslog message storage."""
    __tablename__ = "syslog_messages"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)

    # Syslog fields
    facility = Column(Integer, nullable=True)
    severity = Column(Integer, nullable=True)
    priority = Column(Integer, nullable=True)

    timestamp = Column(DateTime(timezone=True), nullable=True)
    hostname = Column(String(255), nullable=True)
    tag = Column(String(100), nullable=True)
    message = Column(Text, nullable=False)

    received_at = Column(DateTime(timezone=True), server_default=func.now())
