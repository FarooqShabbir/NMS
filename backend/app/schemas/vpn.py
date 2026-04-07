"""Pydantic schemas for VPN endpoints."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TunnelStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class IKEPhase1Status(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    NEGOTIATING = "negotiating"
    FAILED = "failed"


class IPSecStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRING = "expiring"
    FAILED = "failed"


# VPN Tunnel Schemas
class VPNTunnelBase(BaseModel):
    tunnel_name: str = Field(..., min_length=1, max_length=255)
    tunnel_interface: Optional[str] = None
    tunnel_type: str  # ipsec, gre, dmvpn
    local_endpoint: Optional[str] = None
    remote_endpoint: Optional[str] = None
    source_interface: Optional[str] = None
    description: Optional[str] = None


class VPNTunnelResponse(VPNTunnelBase):
    id: int
    device_id: int
    status: TunnelStatus
    ike_version: Optional[int] = None
    ike_phase1_status: Optional[IKEPhase1Status] = None
    ipsec_status: Optional[IPSecStatus] = None
    encryption_algorithm: Optional[str] = None
    uptime: int
    bytes_encrypted: int = 0
    bytes_decrypted: int = 0
    packets_dropped: int = 0
    last_state_change: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VPNTunnelUpdate(BaseModel):
    description: Optional[str] = None


# NHRP Cache Schema (DMVPN)
class NHRPCacheResponse(BaseModel):
    id: int
    device_id: int
    protocol_ip: str
    nbma_ip: str
    tunnel_interface: Optional[str] = None
    entry_type: str
    remaining_time: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# IPSec SA Schema
class IPSecSAResponse(BaseModel):
    id: int
    tunnel_id: Optional[int] = None
    device_id: int
    sa_index: int
    direction: Optional[str] = None
    status: IPSecStatus
    encryption_algorithm: Optional[str] = None
    bytes_processed: int = 0
    remaining_seconds: int = 0
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Summary schemas
class VPNSummaryResponse(BaseModel):
    device_id: int
    total_tunnels: int = 0
    tunnels_up: int = 0
    tunnels_down: int = 0
    dmvpn_spokes: int = 0
    ipsec_sas_active: int = 0
    last_updated: Optional[datetime] = None


class DMVPNHubSummary(BaseModel):
    hub_device_id: int
    hub_name: str
    total_spokes: int
    spokes_connected: int
    spokes_disconnected: int
    tunnel_interface: str
    nhrp_cache_entries: int
