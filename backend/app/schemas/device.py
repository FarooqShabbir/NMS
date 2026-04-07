"""Pydantic schemas for device endpoints."""
from pydantic import BaseModel, Field, IPvAnyAddress, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DeviceType(str, Enum):
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    PRINTER = "printer"
    ACCESS_POINT = "access_point"
    OTHER = "other"


class DeviceStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    UNKNOWN = "unknown"


class SNMPVersion(str, Enum):
    V1 = "v1"
    V2C = "v2c"
    V3 = "v3"


# Device Schemas
class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ip_address: IPvAnyAddress
    description: Optional[str] = None
    device_type: DeviceType = DeviceType.OTHER
    location: Optional[str] = None
    department: Optional[str] = None
    group_id: Optional[int] = None
    polling_enabled: bool = True
    polling_interval: int = Field(default=60, ge=30, le=3600)


class DeviceSNMPConfig(BaseModel):
    snmp_version: SNMPVersion = SNMPVersion.V2C
    snmp_community: Optional[str] = None
    snmp_v3_username: Optional[str] = None
    snmp_v3_auth_protocol: Optional[str] = None
    snmp_v3_auth_password: Optional[str] = None
    snmp_v3_priv_protocol: Optional[str] = None
    snmp_v3_priv_password: Optional[str] = None


class DeviceSSHConfig(BaseModel):
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_key: Optional[str] = None
    ssh_port: int = Field(default=22, ge=1, le=65535)


class DeviceCreate(DeviceBase, DeviceSNMPConfig, DeviceSSHConfig):
    """Schema for creating a new device."""
    pass


class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    ip_address: Optional[IPvAnyAddress] = None
    description: Optional[str] = None
    device_type: Optional[DeviceType] = None
    location: Optional[str] = None
    department: Optional[str] = None
    group_id: Optional[int] = None
    polling_enabled: Optional[bool] = None
    polling_interval: Optional[int] = Field(None, ge=30, le=3600)
    snmp_community: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_port: Optional[int] = None


class DeviceResponse(DeviceBase):
    id: int
    status: DeviceStatus
    snmp_version: SNMPVersion
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceHealthResponse(BaseModel):
    device_id: int
    cpu_usage: float
    memory_usage: float
    memory_total: Optional[int] = None
    memory_used: Optional[int] = None
    disk_usage: Optional[float] = None
    temperature: Optional[float] = None
    uptime: int
    last_polled: datetime


class DeviceDetailResponse(DeviceResponse):
    """Extended device response with relationships."""
    interfaces: List["InterfaceResponse"] = []
    bgp_neighbors: List["BGPNeighborResponse"] = []
    ospf_neighbors: List["OSPFNeighborResponse"] = []
    eigrp_neighbors: List["EIGRPNeighborResponse"] = []
    vpn_tunnels: List["VPNTunnelResponse"] = []
    health: Optional[DeviceHealthResponse] = None


# Interface Schemas
class InterfaceBase(BaseModel):
    name: str
    description: Optional[str] = None


class InterfaceCreate(InterfaceBase):
    if_index: int


class InterfaceResponse(InterfaceBase):
    id: int
    device_id: int
    if_index: int
    mac_address: Optional[str] = None
    ip_address: Optional[str] = None
    oper_status: str
    admin_status: str
    speed: Optional[int] = None
    in_octets: int = 0
    out_octets: int = 0
    utilization_in: float = 0.0
    utilization_out: float = 0.0
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Device Group Schemas
class DeviceGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class DeviceGroupCreate(DeviceGroupBase):
    pass


class DeviceGroupResponse(DeviceGroupBase):
    id: int
    created_at: datetime
    device_count: int = 0

    class Config:
        from_attributes = True


# Import delayed to avoid circular imports
from .routing import BGPNeighborResponse, OSPFNeighborResponse, EIGRPNeighborResponse
from .vpn import VPNTunnelResponse

# Rebuild model to resolve forward references (required by Pydantic v2)
DeviceDetailResponse.model_rebuild()
