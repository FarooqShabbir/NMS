"""SQLAlchemy models - all imports."""
from .device import (
    Device,
    DeviceGroup,
    Interface,
    DeviceHealth,
    DeviceType,
    DeviceStatus,
    SNMPVersion,
)
from .routing import (
    BGPNeighbor,
    OSPFNeighbor,
    OSPFProcess,
    EIGRPNeighbor,
    EIGRPProcess,
    BGPState,
    OSPFState,
)
from .vpn import (
    VPNTunnel,
    NHRPCache,
    IPSecSA,
    TunnelStatus,
    IKEPhase1Status,
    IPSecStatus,
)
from .backup import (
    DeviceBackup,
    BackupSchedule,
    ConfigChange,
    BackupMethod,
    BackupStatus,
    BackupType,
)
from .alert import (
    Alert,
    AlertRule,
    MaintenanceWindow,
    SyslogMessage,
    AlertSeverity,
    AlertStatus,
    AlertType,
)
from .user import (
    User,
    AuditLog,
    UserRole,
)

__all__ = [
    # Device
    "Device", "DeviceGroup", "Interface", "DeviceHealth",
    "DeviceType", "DeviceStatus", "SNMPVersion",
    # Routing
    "BGPNeighbor", "OSPFNeighbor", "OSPFProcess",
    "EIGRPNeighbor", "EIGRPProcess", "BGPState", "OSPFState",
    # VPN
    "VPNTunnel", "NHRPCache", "IPSecSA",
    "TunnelStatus", "IKEPhase1Status", "IPSecStatus",
    # Backup
    "DeviceBackup", "BackupSchedule", "ConfigChange",
    "BackupMethod", "BackupStatus", "BackupType",
    # Alert
    "Alert", "AlertRule", "MaintenanceWindow", "SyslogMessage",
    "AlertSeverity", "AlertStatus", "AlertType",
    # User
    "User", "AuditLog", "UserRole",
]
