"""Device health polling service - CPU, Memory, Interface stats."""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.device import Device, DeviceHealth, Interface, DeviceStatus
from ..utils.oid_mappings import (
    # System
    SYS_DESCR,
    SYS_UPTIME,
    # Interfaces
    IF_NUMBER,
    IF_ENTRY,
    IF_NAME,
    IF_DESCR,
    IF_OPER_STATUS,
    IF_ADMIN_STATUS,
    IF_IN_OCTETS,
    IF_OUT_OCTETS,
    IF_IN_ERRORS,
    IF_OUT_ERRORS,
    IF_IN_DISCARDS,
    IF_OUT_DISCARDS,
    IF_SPEED,
    IF_TYPE,
    IF_STATUS_UP,
    IF_STATUS_DOWN,
    # CPU/Memory (Cisco)
    CISCO_CPU_5SEC,
    CISCO_MEMORY_USED,
    CISCO_MEMORY_FREE,
    # Generic
    MEM_POOL_USED,
    MEM_POOL_FREE,
    get_if_status_name,
)
from .snmp_service import snmp_service, SNMPError


class DeviceHealthService:
    """Service for polling device health metrics."""

    def __init__(self, db: Session):
        self.db = db
        self.snmp = snmp_service

    def poll_device_health(self, device: Device) -> Optional[Dict[str, Any]]:
        """
        Poll device health metrics (CPU, Memory, Uptime).

        Returns dict with health data or None if polling failed.
        """
        health_data = {}

        try:
            # Get uptime
            uptime = self.snmp.get_value(SYS_UPTIME, device)
            if uptime:
                # TimeTicks to seconds
                health_data["uptime"] = int(uptime) // 100

            # Try Cisco CPU first
            cpu = self.snmp.get_value(CISCO_CPU_5SEC, device)
            if cpu is not None:
                health_data["cpu_usage"] = float(cpu)
            else:
                # Try generic memory/health OIDs
                # UCD-SNMP-MIB for Linux/Unix
                health_data["cpu_usage"] = 0.0  # Would need additional polling

            # Try Cisco memory
            mem_used = self.snmp.get_value(CISCO_MEMORY_USED, device)
            mem_free = self.snmp.get_value(CISCO_MEMORY_FREE, device)

            if mem_used is not None and mem_free is not None:
                total = int(mem_used) + int(mem_free)
                health_data["memory_used"] = int(mem_used) * 1024  # Convert to bytes
                health_data["memory_total"] = total * 1024
                health_data["memory_usage"] = (int(mem_used) / total) * 100 if total > 0 else 0
            else:
                # Try generic memory OIDs
                mem_total = self.snmp.get_value(MEM_POOL_USED, device)
                mem_free = self.snmp.get_value(MEM_POOL_FREE, device)
                if mem_total is not None and mem_free is not None:
                    total = int(mem_total)
                    used = total - int(mem_free)
                    health_data["memory_used"] = used * 1024
                    health_data["memory_total"] = total * 1024
                    health_data["memory_usage"] = (used / total) * 100 if total > 0 else 0

        except SNMPError:
            return None

        return health_data

    def poll_interfaces(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll interface statistics.

        Returns list of interface data.
        """
        interfaces = []

        try:
            # Walk interface table
            if_data = {}

            # Get interface names/descriptions
            for suffix, value in self.snmp.walk(IF_NAME, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index not in if_data:
                    if_data[if_index] = {"if_index": if_index}
                if_data[if_index]["name"] = str(value)

            for suffix, value in self.snmp.walk(IF_DESCR, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["description"] = str(value)

            # Get interface status
            for suffix, value in self.snmp.walk(IF_OPER_STATUS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["oper_status"] = get_if_status_name(int(value))
                    if_data[if_index]["oper_status_raw"] = int(value)

            for suffix, value in self.snmp.walk(IF_ADMIN_STATUS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["admin_status"] = get_if_status_name(int(value))

            # Get interface statistics
            for suffix, value in self.snmp.walk(IF_IN_OCTETS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["in_octets"] = int(value)

            for suffix, value in self.snmp.walk(IF_OUT_OCTETS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["out_octets"] = int(value)

            for suffix, value in self.snmp.walk(IF_IN_ERRORS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["in_errors"] = int(value)

            for suffix, value in self.snmp.walk(IF_OUT_ERRORS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["out_errors"] = int(value)

            for suffix, value in self.snmp.walk(IF_IN_DISCARDS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["in_discards"] = int(value)

            for suffix, value in self.snmp.walk(IF_OUT_DISCARDS, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["out_discards"] = int(value)

            for suffix, value in self.snmp.walk(IF_SPEED, device).items():
                if_index = int(suffix.split(".")[-1]) if "." in suffix else int(suffix)
                if if_index in if_data:
                    if_data[if_index]["speed"] = int(value)

            interfaces = list(if_data.values())

        except SNMPError:
            pass

        return interfaces

    def save_device_health(
        self,
        device: Device,
        health_data: Dict[str, Any],
    ) -> DeviceHealth:
        """Save device health to database."""
        health = (
            self.db.query(DeviceHealth)
            .filter(DeviceHealth.device_id == device.id)
            .first()
        )

        if not health:
            health = DeviceHealth(device_id=device.id)

        health.cpu_usage = health_data.get("cpu_usage", 0.0)
        health.memory_usage = health_data.get("memory_usage", 0.0)
        health.memory_total = health_data.get("memory_total", 0)
        health.memory_used = health_data.get("memory_used", 0)
        health.disk_usage = health_data.get("disk_usage", 0.0)
        health.temperature = health_data.get("temperature")
        health.uptime = health_data.get("uptime", 0)
        health.last_polled = datetime.utcnow()

        self.db.add(health)
        self.db.commit()
        self.db.refresh(health)

        return health

    def save_interfaces(
        self,
        device: Device,
        interface_data: List[Dict[str, Any]],
    ) -> int:
        """Save interface data to database."""
        count = 0

        for data in interface_data:
            if_index = data.get("if_index")
            if if_index is None:
                continue

            interface = (
                self.db.query(Interface)
                .filter(
                    Interface.device_id == device.id,
                    Interface.if_index == if_index,
                )
                .first()
            )

            if not interface:
                interface = Interface(device_id=device.id)

            interface.if_index = if_index
            interface.name = data.get("name", f"if{if_index}")
            interface.description = data.get("description")
            interface.oper_status = data.get("oper_status", "unknown")
            interface.admin_status = data.get("admin_status", "unknown")
            interface.in_octets = data.get("in_octets", 0)
            interface.out_octets = data.get("out_octets", 0)
            interface.in_errors = data.get("in_errors", 0)
            interface.out_errors = data.get("out_errors", 0)
            interface.in_discards = data.get("in_discards", 0)
            interface.out_discards = data.get("out_discards", 0)
            interface.speed = data.get("speed")

            # Calculate utilization (would need previous values for accurate calc)
            if interface.speed and interface.speed > 0:
                # Simplified - would need delta calculation in production
                interface.utilization_in = 0.0
                interface.utilization_out = 0.0

            self.db.add(interface)
            count += 1

        self.db.commit()
        return count

    def update_device_status(self, device: Device) -> DeviceStatus:
        """Update device status based on health check."""
        # Try to ping device via SNMP
        try:
            self.snmp.get_value(SYS_DESCR, device)
            device.status = DeviceStatus.UP
        except SNMPError:
            device.status = DeviceStatus.DOWN

        self.db.add(device)
        self.db.commit()
        return device.status


# Factory function
def get_device_health_service(db: Session):
    """Get device health service instance."""
    return DeviceHealthService(db)
