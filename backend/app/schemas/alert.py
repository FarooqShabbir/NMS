"""Pydantic schemas for alert endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertType(str, Enum):
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


# Alert Schemas
class AlertBase(BaseModel):
    alert_type: AlertType
    severity: AlertSeverity
    title: str = Field(..., min_length=1, max_length=255)
    message: str


class AlertCreate(AlertBase):
    device_id: Optional[int] = None
    interface_id: Optional[int] = None
    details: Optional[str] = None
    threshold_value: Optional[float] = None
    current_value: Optional[float] = None


class AlertResponse(AlertBase):
    id: int
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    status: AlertStatus
    triggered_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    notification_count: int = 0

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    status: Optional[AlertStatus] = None
    acknowledgment_note: Optional[str] = None


class AlertAcknowledgeRequest(BaseModel):
    acknowledgment_note: Optional[str] = None


# Alert Rule Schemas
class AlertRuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    enabled: bool = True
    alert_type: AlertType
    severity: AlertSeverity = AlertSeverity.WARNING
    metric: Optional[str] = None
    operator: Optional[str] = None  # gt, lt, eq, ne
    threshold_value: Optional[float] = None
    duration_seconds: int = Field(default=0, ge=0)
    notify_email: bool = False
    notify_slack: bool = False
    notify_telegram: bool = False
    notify_webhook: bool = False
    webhook_url: Optional[str] = None


class AlertRuleCreate(AlertRuleBase):
    device_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None


class AlertRuleResponse(AlertRuleBase):
    id: int
    device_ids: Optional[List[int]] = None
    group_ids: Optional[List[int]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[AlertSeverity] = None
    threshold_value: Optional[float] = None
    notify_email: Optional[bool] = None
    notify_slack: Optional[bool] = None
    notify_telegram: Optional[bool] = None


# Maintenance Window Schemas
class MaintenanceWindowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    recurring: bool = False
    device_ids: Optional[List[int]] = None
    alert_types: Optional[List[AlertType]] = None
    suppress_notifications: bool = True


class MaintenanceWindowCreate(MaintenanceWindowBase):
    pass


class MaintenanceWindowResponse(MaintenanceWindowBase):
    id: int
    created_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Dashboard/Summary Schemas
class AlertSummaryResponse(BaseModel):
    total_alerts: int = 0
    active_alerts: int = 0
    acknowledged_alerts: int = 0
    critical_alerts: int = 0
    warning_alerts: int = 0
    alerts_by_type: dict = {}
    alerts_by_severity: dict = {}


class AlertTimelineResponse(BaseModel):
    timestamp: datetime
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    device_name: Optional[str] = None
    status: AlertStatus
