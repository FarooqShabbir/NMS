"""Routing protocol SQLAlchemy models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, JSON, BigInteger
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class BGPState(str, enum.Enum):
    """BGP neighbor state enumeration."""
    IDLE = "idle"
    CONNECT = "connect"
    ACTIVE = "active"
    OPEN_SENT = "open_sent"
    OPEN_CONFIRM = "open_confirm"
    ESTABLISHED = "established"


class OSPFState(str, enum.Enum):
    """OSPF neighbor state enumeration."""
    DOWN = "down"
    ATTEMPT = "attempt"
    INIT = "init"
    TWO_WAY = "two_way"
    EX_START = "ex_start"
    EXCHANGE = "exchange"
    LOADING = "loading"
    FULL = "full"


class BGPNeighbor(Base):
    """BGP neighbor model."""
    __tablename__ = "bgp_neighbors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # Neighbor identification
    neighbor_ip = Column(String(45), nullable=False)
    neighbor_as = Column(Integer, nullable=False)
    local_as = Column(Integer, nullable=False)

    # State
    state = Column(SQLEnum(BGPState), default=BGPState.IDLE)
    admin_status = Column(String(20), default="unknown")  # enabled, disabled

    # Statistics
    prefixes_received = Column(Integer, default=0)
    prefixes_sent = Column(Integer, default=0)
    messages_received = Column(BigInteger, default=0)
    messages_sent = Column(BigInteger, default=0)

    # Timing
    uptime = Column(BigInteger, default=0)  # seconds
    last_flap = Column(DateTime(timezone=True), nullable=True)
    flap_count = Column(Integer, default=0)

    # Configuration
    description = Column(String(255), nullable=True)
    password_enabled = Column(Boolean, default=False)
    hold_time = Column(Integer, default=180)
    keepalive_time = Column(Integer, default=60)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="bgp_neighbors")


class OSPFNeighbor(Base):
    """OSPF neighbor model."""
    __tablename__ = "ospf_neighbors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # Neighbor identification
    neighbor_ip = Column(String(45), nullable=False)
    neighbor_id = Column(String(15), nullable=False)  # Router ID
    local_interface = Column(String(255), nullable=True)
    local_interface_ip = Column(String(45), nullable=True)

    # State
    state = Column(SQLEnum(OSPFState), default=OSPFState.DOWN)

    # Area
    area_id = Column(String(15), nullable=True)

    # Timing
    uptime = Column(BigInteger, default=0)  # seconds
    dead_timer = Column(Integer, default=40)
    hello_interval = Column(Integer, default=10)

    # Statistics
    retransmissions = Column(BigInteger, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="ospf_neighbors")


class OSPFProcess(Base):
    """OSPF process model."""
    __tablename__ = "ospf_processes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    process_id = Column(Integer, nullable=False)
    router_id = Column(String(15), nullable=True)
    admin_status = Column(String(20), default="unknown")

    areas = Column(JSON, default=list)  # List of area IDs

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class EIGRPNeighbor(Base):
    """EIGRP neighbor model."""
    __tablename__ = "eigrp_neighbors"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    # Neighbor identification
    neighbor_ip = Column(String(45), nullable=False)
    local_interface = Column(String(255), nullable=True)

    # AS and K-values
    autonomous_system = Column(Integer, nullable=False)
    k1 = Column(Integer, default=1)
    k2 = Column(Integer, default=0)
    k3 = Column(Integer, default=1)
    k4 = Column(Integer, default=0)
    k5 = Column(Integer, default=0)

    # State
    uptime = Column(BigInteger, default=0)  # seconds
    hold_time = Column(Integer, default=15)
    srtt = Column(Integer, default=0)  # Smooth Round Trip Time (ms)
    rto = Column(Integer, default=0)  # Retransmit Timeout (ms)

    # Queue counts
    queue_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="eigrp_neighbors")


class EIGRPProcess(Base):
    """EIGRP process model."""
    __tablename__ = "eigrp_processes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)

    autonomous_system = Column(Integer, nullable=False)
    router_id = Column(String(15), nullable=True)
    admin_status = Column(String(20), default="unknown")

    # Topology stats
    successor_count = Column(Integer, default=0)
    feasible_successor_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
