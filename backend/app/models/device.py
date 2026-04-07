"""Device and related SQLAlchemy models."""
from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from ..core.database import Base


class DeviceType(str, enum.Enum):
    """Device type enumeration."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    PRINTER = "printer"
    ACCESS_POINT = "access_point"
    OTHER = "other"


class DeviceStatus(str, enum.Enum):
    """Device status enumeration."""
    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    UNKNOWN = "unknown"


class SNMPVersion(str, enum.Enum):
    """SNMP version enumeration."""
    V1 = "v1"
    V2C = "v2c"
    V3 = "v3"


class Device(Base):
    """Network device model."""
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    ip_address = Column(String(45), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Device type and status
    device_type = Column(SQLEnum(DeviceType), default=DeviceType.OTHER)
    status = Column(SQLEnum(DeviceStatus), default=DeviceStatus.UNKNOWN)

    # SNMP Configuration
    snmp_version = Column(SQLEnum(SNMPVersion), default=SNMPVersion.V2C)
    snmp_community = Column(String(255), nullable=True)  # For v1/v2c
    snmp_v3_username = Column(String(255), nullable=True)
    snmp_v3_auth_protocol = Column(String(10), nullable=True)  # MD5, SHA
    snmp_v3_auth_password = Column(String(255), nullable=True)
    snmp_v3_priv_protocol = Column(String(10), nullable=True)  # DES, AES
    snmp_v3_priv_password = Column(String(255), nullable=True)

    # SSH credentials for backups
    ssh_username = Column(String(255), nullable=True)
    ssh_password = Column(String(255), nullable=True)
    ssh_key = Column(Text, nullable=True)
    ssh_port = Column(Integer, default=22)

    # Location and grouping
    location = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=True)

    # Polling configuration
    polling_enabled = Column(Boolean, default=True)
    polling_interval = Column(Integer, default=60)  # seconds

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    group = relationship("DeviceGroup", back_populates="devices")
    interfaces = relationship("Interface", back_populates="device", cascade="all, delete-orphan")
    bgp_neighbors = relationship("BGPNeighbor", back_populates="device", cascade="all, delete-orphan")
    ospf_neighbors = relationship("OSPFNeighbor", back_populates="device", cascade="all, delete-orphan")
    eigrp_neighbors = relationship("EIGRPNeighbor", back_populates="device", cascade="all, delete-orphan")
    vpn_tunnels = relationship("VPNTunnel", back_populates="device", cascade="all, delete-orphan")
    backups = relationship("DeviceBackup", back_populates="device", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete-orphan")


class DeviceGroup(Base):
    """Device group for organizing devices."""
    __tablename__ = "device_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    devices = relationship("Device", back_populates="group")


class Interface(Base):
    """Network interface model."""
    __tablename__ = "interfaces"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    if_index = Column(Integer, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(255), nullable=True)
    mac_address = Column(String(17), nullable=True)
    ip_address = Column(String(45), nullable=True)
    subnet_mask = Column(String(15), nullable=True)
    mtu = Column(Integer, nullable=True)
    speed = Column(BigInteger, nullable=True)  # bits per second
    duplex = Column(String(10), nullable=True)  # full, half
    admin_status = Column(String(20), default="unknown")  # up, down
    oper_status = Column(String(20), default="unknown")  # up, down
    if_type = Column(String(50), nullable=True)

    # Current stats (updated by polling)
    in_octets = Column(BigInteger, default=0)
    out_octets = Column(BigInteger, default=0)
    in_unicast_packets = Column(BigInteger, default=0)
    out_unicast_packets = Column(BigInteger, default=0)
    in_errors = Column(BigInteger, default=0)
    out_errors = Column(BigInteger, default=0)
    in_discards = Column(BigInteger, default=0)
    out_discards = Column(BigInteger, default=0)
    utilization_in = Column(Float, default=0.0)  # percentage
    utilization_out = Column(Float, default=0.0)  # percentage

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    device = relationship("Device", back_populates="interfaces")


class DeviceHealth(Base):
    """Device health metrics (latest values)."""
    __tablename__ = "device_health"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, unique=True)

    cpu_usage = Column(Float, default=0.0)  # percentage
    memory_usage = Column(Float, default=0.0)  # percentage
    memory_total = Column(BigInteger, default=0)  # bytes
    memory_used = Column(BigInteger, default=0)  # bytes
    disk_usage = Column(Float, default=0.0)  # percentage
    temperature = Column(Float, nullable=True)  # celsius
    fan_status = Column(String(50), nullable=True)
    power_status = Column(String(50), nullable=True)
    uptime = Column(BigInteger, default=0)  # seconds

    last_polled = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

