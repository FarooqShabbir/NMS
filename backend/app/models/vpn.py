"""VPN and DMVPN SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class TunnelStatus(str, enum.Enum):
    """Tunnel status enumeration."""
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class IKEPhase1Status(str, enum.Enum):
    """IKE Phase 1 status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    NEGOTIATING = "negotiating"
    FAILED = "failed"


class IPSecStatus(str, enum.Enum):
    """IPSec SA status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRING = "expiring"
    FAILED = "failed"


class VPNTunnel(Base):
    """VPN Tunnel model (IPSec, GRE, DMVPN)."""
    __tablename__ = "vpn_tunnels"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # Tunnel identification
    tunnel_name = Column(String(255), nullable=False)
    tunnel_interface = Column(String(50), nullable=True)
    tunnel_type = Column(String(20), nullable=False)  # ipsec, gre, dmvpn

    # Status
    status = Column(SQLEnum(TunnelStatus), default=TunnelStatus.UNKNOWN)

    # Endpoint configuration
    local_endpoint = Column(String(45), nullable=True)
    remote_endpoint = Column(String(45), nullable=True)
    source_interface = Column(String(50), nullable=True)

    # IPSec specific
    ike_version = Column(Integer, default=2)  # 1 or 2
    ike_phase1_status = Column(SQLEnum(IKEPhase1Status), default=IKEPhase1Status.INACTIVE)
    ipsec_status = Column(SQLEnum(IPSecStatus), default=IPSecStatus.INACTIVE)
    encryption_algorithm = Column(String(50), nullable=True)
    authentication_algorithm = Column(String(50), nullable=True)

    # Statistics
    bytes_encrypted = Column(BigInteger, default=0)
    bytes_decrypted = Column(BigInteger, default=0)
    packets_encrypted = Column(BigInteger, default=0)
    packets_decrypted = Column(BigInteger, default=0)
    bytes_dropped = Column(BigInteger, default=0)
    packets_dropped = Column(BigInteger, default=0)

    # Timing
    uptime = Column(BigInteger, default=0)  # seconds
    last_state_change = Column(DateTime(timezone=True), nullable=True)

    # DMVPN specific
    nhrp_peer_type = Column(String(20), nullable=True)  # hub, spoke
    nbma_address = Column(String(45), nullable=True)  # NBMA (underlay) address
    tunnel_vrf = Column(String(50), nullable=True)

    # Metadata
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="vpn_tunnels")


class NHRPCache(Base):
    """DMVPN NHRP cache entry model."""
    __tablename__ = "nhrp_cache"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # NHRP entry
    protocol_ip = Column(String(45), nullable=False)  # NBMA address
    nbma_ip = Column(String(45), nullable=False)
    tunnel_interface = Column(String(50), nullable=True)

    # Type
    entry_type = Column(String(20), default="dynamic")  # static, dynamic

    # Timing
    remaining_time = Column(Integer, default=0)  # seconds until expiration

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class IPSecSA(Base):
    """IPSec Security Association model."""
    __tablename__ = "ipsec_sas"

    id = Column(Integer, primary_key=True, index=True)
    tunnel_id = Column(Integer, ForeignKey("vpn_tunnels.id"), nullable=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # SA identification
    sa_index = Column(Integer, nullable=False)
    direction = Column(String(10), nullable=True)  # inbound, outbound

    # Status
    status = Column(SQLEnum(IPSecStatus), default=IPSecStatus.INACTIVE)

    # Encryption
    encryption_algorithm = Column(String(50), nullable=True)
    authentication_algorithm = Column(String(50), nullable=True)

    # Statistics
    bytes_processed = Column(BigInteger, default=0)
    packets_processed = Column(BigInteger, default=0)

    # Lifetime
    lifetime_seconds = Column(Integer, default=28800)
    remaining_seconds = Column(Integer, default=0)
    lifetime_kb = Column(Integer, default=4608000)  # 4.6GB default
    remaining_kb = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
