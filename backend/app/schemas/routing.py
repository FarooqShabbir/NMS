"""Pydantic schemas for routing protocol endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class BGPState(str, Enum):
    IDLE = "idle"
    CONNECT = "connect"
    ACTIVE = "active"
    OPEN_SENT = "open_sent"
    OPEN_CONFIRM = "open_confirm"
    ESTABLISHED = "established"


class OSPFState(str, Enum):
    DOWN = "down"
    ATTEMPT = "attempt"
    INIT = "init"
    TWO_WAY = "two_way"
    EX_START = "ex_start"
    EXCHANGE = "exchange"
    LOADING = "loading"
    FULL = "full"


# BGP Neighbor Schemas
class BGPNeighborBase(BaseModel):
    neighbor_ip: str
    neighbor_as: int
    local_as: int
    description: Optional[str] = None


class BGPNeighborResponse(BGPNeighborBase):
    id: int
    device_id: int
    state: BGPState
    admin_status: str
    prefixes_received: int
    prefixes_sent: int
    uptime: int
    flap_count: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BGPNeighborUpdate(BaseModel):
    admin_status: Optional[str] = None
    description: Optional[str] = None


# OSPF Neighbor Schemas
class OSPFNeighborBase(BaseModel):
    neighbor_ip: str
    neighbor_id: str  # Router ID
    area_id: Optional[str] = None
    local_interface: Optional[str] = None


class OSPFNeighborResponse(OSPFNeighborBase):
    id: int
    device_id: int
    state: OSPFState
    uptime: int
    hello_interval: int
    dead_timer: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OSPFProcessResponse(BaseModel):
    id: int
    device_id: int
    process_id: int
    router_id: Optional[str] = None
    admin_status: str
    areas: List[str]
    neighbor_count: int = 0
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# EIGRP Neighbor Schemas
class EIGRPNeighborBase(BaseModel):
    neighbor_ip: str
    autonomous_system: int
    local_interface: Optional[str] = None


class EIGRPNeighborResponse(EIGRPNeighborBase):
    id: int
    device_id: int
    uptime: int
    hold_time: int
    srtt: int
    rto: int
    queue_count: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EIGRPProcessResponse(BaseModel):
    id: int
    device_id: int
    autonomous_system: int
    router_id: Optional[str] = None
    admin_status: str
    successor_count: int
    feasible_successor_count: int
    neighbor_count: int = 0
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Summary schemas
class RoutingSummaryResponse(BaseModel):
    device_id: int
    bgp_neighbors_count: int = 0
    bgp_established_count: int = 0
    ospf_neighbors_count: int = 0
    ospf_full_count: int = 0
    eigrp_neighbors_count: int = 0
    eigrp_established_count: int = 0
    last_updated: Optional[datetime] = None
