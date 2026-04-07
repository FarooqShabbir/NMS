"""Routing protocol service - BGP, OSPF, EIGRP polling via SNMP."""
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.routing import BGPNeighbor, OSPFNeighbor, EIGRPNeighbor, BGPState, OSPFState
from ..utils.oid_mappings import (
    # OSPF
    OSPF_NEIGHBOR_TABLE,
    OSPF_NEIGHBOR_IP,
    OSPF_NEIGHBOR_ROUTER_ID,
    OSPF_NEIGHBOR_STATE,
    OSPF_NEIGHBOR_IF_INDEX,
    OSPF_NEIGHBOR_HELLO_INTERVAL,
    OSPF_NEIGHBOR_DEAD_INTERVAL,
    OSPF_NEIGHBOR_EVENTS,
    OSPF_AREA_TABLE,
    OSPF_AREA_ID,
    OSPF_ROUTER_ID,
    get_ospf_state_name,
    # BGP
    BGP_PEER_TABLE,
    BGP_PEER_IP,
    BGP_PEER_STATE,
    BGP_PEER_ADMIN_STATUS,
    BGP_PEER_LOCAL_AS,
    BGP_PEER_REMOTE_AS,
    BGP_PEER_UPTIME,
    BGP4_PREFIX_COUNT,
    get_bgp_state_name,
    # EIGRP
    EIGRP_NEIGHBOR_TABLE,
    EIGRP_NEIGHBOR_IP,
    EIGRP_NEIGHBOR_IF_INDEX,
    EIGRP_NEIGHBOR_UPTIME,
    EIGRP_NEIGHBOR_HOLD_TIME,
    EIGRP_NEIGHBOR_SRTT,
    EIGRP_NEIGHBOR_RTO,
    EIGRP_NEIGHBOR_QUEUE_COUNT,
    EIGRP_ASN,
)
from .snmp_service import snmp_service


class RoutingService:
    """Service for polling routing protocol information."""

    def __init__(self, db: Session):
        self.db = db
        self.snmp = snmp_service

    # ============================================
    # OSPF Methods
    # ============================================

    def poll_ospf_neighbors(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll OSPF neighbor information from device.

        Returns list of OSPF neighbor data.
        """
        neighbors = []

        try:
            # Walk OSPF neighbor table
            # OID format: 1.3.6.1.2.1.14.10.1.X.{area_ip}.{neighbor_ip}
            neighbor_data = self.snmp.walk(OSPF_NEIGHBOR_TABLE, device)

            # Group data by neighbor
            neighbor_entries = {}

            for suffix, value in neighbor_data.items():
                parts = suffix.split(".")
                if len(parts) < 3:
                    continue

                # Parse OID to get area and neighbor IP
                # Format: {column}.{area_octets}.{neighbor_octets}
                column = parts[0]
                # Area is typically 4 octets (for IPv4-style area ID)
                area_octets = parts[1:5] if len(parts) >= 5 else ["0", "0", "0", "1"]
                neighbor_octets = parts[5:] if len(parts) > 5 else parts[1:]

                try:
                    area_ip = ".".join(area_octets[:4])
                    neighbor_ip = ".".join(neighbor_octets[:4])
                except Exception:
                    continue

                if neighbor_ip not in neighbor_entries:
                    neighbor_entries[neighbor_ip] = {
                        "neighbor_ip": neighbor_ip,
                        "area_id": area_ip,
                    }

                # Map column to value
                if column == "6":  # ospfNbrState
                    neighbor_entries[neighbor_ip]["state"] = get_ospf_state_name(int(value))
                    neighbor_entries[neighbor_ip]["state_raw"] = int(value)
                elif column == "3":  # ospfNbrRtrId
                    neighbor_entries[neighbor_ip]["router_id"] = str(value)
                elif column == "13":  # ospfNbrHelloInterval
                    neighbor_entries[neighbor_ip]["hello_interval"] = int(value)
                elif column == "14":  # ospfNbrRtrDeadInterval
                    neighbor_entries[neighbor_ip]["dead_timer"] = int(value)
                elif column == "7":  # ospfNbrEvents
                    neighbor_entries[neighbor_ip]["events"] = int(value)

            neighbors = list(neighbor_entries.values())

        except Exception as e:
            # OSPF might not be enabled on device
            pass

        return neighbors

    def poll_ospf_processes(self, device: Device) -> List[Dict[str, Any]]:
        """Poll OSPF process information."""
        processes = []

        try:
            # Get router ID
            router_id = self.snmp.get_value(OSPF_ROUTER_ID, device)

            # Walk area table
            areas = []
            area_data = self.snmp.walk(OSPF_AREA_TABLE, device)

            for suffix, value in area_data.items():
                parts = suffix.split(".")
                if parts[0] == "1" and len(parts) >= 5:  # ospfAreaId
                    area_ip = ".".join(parts[1:5])
                    areas.append(area_ip)

            if router_id or areas:
                processes.append({
                    "router_id": str(router_id) if router_id else None,
                    "areas": list(set(areas)),
                })

        except Exception:
            pass

        return processes

    def save_ospf_neighbors(
        self,
        device: Device,
        neighbor_data: List[Dict[str, Any]],
    ) -> int:
        """
        Save OSPF neighbor data to database.

        Returns number of neighbors saved.
        """
        count = 0

        for data in neighbor_data:
            neighbor_ip = data.get("neighbor_ip")
            if not neighbor_ip:
                continue

            # Find existing or create new
            neighbor = (
                self.db.query(OSPFNeighbor)
                .filter(
                    OSPFNeighbor.device_id == device.id,
                    OSPFNeighbor.neighbor_ip == neighbor_ip,
                )
                .first()
            )

            if not neighbor:
                neighbor = OSPFNeighbor(device_id=device.id)

            neighbor.neighbor_ip = neighbor_ip
            neighbor.neighbor_id = data.get("router_id", "")
            neighbor.area_id = data.get("area_id")
            neighbor.state = data.get("state", OSPFState.DOWN)
            neighbor.hello_interval = data.get("hello_interval", 10)
            neighbor.dead_timer = data.get("dead_timer", 40)
            neighbor.uptime = 0  # Would need additional polling for uptime

            self.db.add(neighbor)
            count += 1

        self.db.commit()
        return count

    # ============================================
    # BGP Methods
    # ============================================

    def poll_bgp_neighbors(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll BGP neighbor information from device.

        Returns list of BGP neighbor data.
        """
        neighbors = []

        try:
            # Walk BGP peer table
            # OID format: 1.3.6.1.2.1.15.3.1.X.{peer_ip}
            peer_data = self.snmp.walk(BGP_PEER_TABLE, device)

            # Group data by peer IP
            peer_entries = {}

            for suffix, value in peer_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                column = parts[0]
                # Peer IP is typically the remaining octets
                peer_ip = ".".join(parts[1:5]) if len(parts) >= 5 else parts[-1]

                if peer_ip not in peer_entries:
                    peer_entries[peer_ip] = {"neighbor_ip": peer_ip}

                # Map column to value
                if column == "2":  # bgpPeerState
                    peer_entries[peer_ip]["state"] = get_bgp_state_name(int(value))
                    peer_entries[peer_ip]["state_raw"] = int(value)
                elif column == "3":  # bgpPeerAdminStatus
                    peer_entries[peer_ip]["admin_status"] = "enabled" if int(value) == 1 else "disabled"
                elif column == "14":  # bgpPeerLocalAs
                    peer_entries[peer_ip]["local_as"] = int(value)
                elif column == "10":  # bgpPeerRemoteAs
                    peer_entries[peer_ip]["neighbor_as"] = int(value)
                elif column == "13":  # bgpPeerFsmEstablishedTime
                    peer_entries[peer_ip]["uptime"] = int(value)

            # Try to get prefix counts (BGP4-MIB)
            try:
                prefix_data = self.snmp.walk(BGP4_PREFIX_COUNT, device)
                for suffix, value in prefix_data.items():
                    parts = suffix.split(".")
                    if len(parts) >= 5:
                        peer_ip = ".".join(parts[1:5])
                        if peer_ip in peer_entries:
                            peer_entries[peer_ip]["prefixes_received"] = int(value)
            except Exception:
                pass

            neighbors = list(peer_entries.values())

        except Exception as e:
            # BGP might not be enabled on device
            pass

        return neighbors

    def save_bgp_neighbors(
        self,
        device: Device,
        neighbor_data: List[Dict[str, Any]],
    ) -> int:
        """
        Save BGP neighbor data to database.

        Returns number of neighbors saved.
        """
        count = 0

        for data in neighbor_data:
            neighbor_ip = data.get("neighbor_ip")
            if not neighbor_ip:
                continue

            neighbor = (
                self.db.query(BGPNeighbor)
                .filter(
                    BGPNeighbor.device_id == device.id,
                    BGPNeighbor.neighbor_ip == neighbor_ip,
                )
                .first()
            )

            if not neighbor:
                neighbor = BGPNeighbor(device_id=device.id)

            neighbor.neighbor_ip = neighbor_ip
            neighbor.neighbor_as = data.get("neighbor_as", 0)
            neighbor.local_as = data.get("local_as", 0)
            neighbor.state = data.get("state", BGPState.IDLE)
            neighbor.admin_status = data.get("admin_status", "unknown")
            neighbor.prefixes_received = data.get("prefixes_received", 0)
            neighbor.uptime = data.get("uptime", 0)

            # Track flaps
            old_state = neighbor.state if neighbor.id else None
            if old_state and old_state != data.get("state"):
                neighbor.flap_count = (neighbor.flap_count or 0) + 1
                neighbor.last_flap = datetime.utcnow()

            self.db.add(neighbor)
            count += 1

        self.db.commit()
        return count

    # ============================================
    # EIGRP Methods
    # ============================================

    def poll_eigrp_neighbors(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll EIGRP neighbor information from device.

        Returns list of EIGRP neighbor data.
        """
        neighbors = []

        try:
            # Walk EIGRP neighbor table
            # OID format: 1.3.6.1.4.1.9.9.91.1.3.1.X.{asn}.{if_index}.{neighbor_ip}
            neighbor_data = self.snmp.walk(EIGRP_NEIGHBOR_TABLE, device)

            # Group data by neighbor
            neighbor_entries = {}
            asn = None

            for suffix, value in neighbor_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                # Parse ASN from OID
                if len(parts) >= 2:
                    try:
                        asn = int(parts[0])
                    except ValueError:
                        pass

                # Neighbor IP is typically at the end
                if len(parts) >= 4:
                    neighbor_ip = ".".join(parts[-4:])
                else:
                    continue

                column = parts[1] if len(parts) > 1 else ""

                if neighbor_ip not in neighbor_entries:
                    neighbor_entries[neighbor_ip] = {
                        "neighbor_ip": neighbor_ip,
                        "autonomous_system": asn,
                    }

                # Map column to value
                # ciscoEigrpNeighborMIB structure
                if column == "2":  # IP address column
                    pass  # Already extracted
                elif column == "5":  # uptime
                    neighbor_entries[neighbor_ip]["uptime"] = int(value)
                elif column == "6":  # hold time
                    neighbor_entries[neighbor_ip]["hold_time"] = int(value)
                elif column == "8":  # SRTT
                    neighbor_entries[neighbor_ip]["srtt"] = int(value)
                elif column == "9":  # RTO
                    neighbor_entries[neighbor_ip]["rto"] = int(value)
                elif column == "11":  # Queue count
                    neighbor_entries[neighbor_ip]["queue_count"] = int(value)

            # Get ASN from EIGRP ASN table
            try:
                asn_data = self.snmp.walk(EIGRP_ASN, device)
                if asn_data:
                    asn = list(asn_data.values())[0]
                    for entry in neighbor_entries.values():
                        entry["autonomous_system"] = int(asn)
            except Exception:
                pass

            neighbors = list(neighbor_entries.values())

        except Exception as e:
            # EIGRP might not be enabled on device
            pass

        return neighbors

    def save_eigrp_neighbors(
        self,
        device: Device,
        neighbor_data: List[Dict[str, Any]],
    ) -> int:
        """
        Save EIGRP neighbor data to database.

        Returns number of neighbors saved.
        """
        count = 0

        for data in neighbor_data:
            neighbor_ip = data.get("neighbor_ip")
            if not neighbor_ip:
                continue

            neighbor = (
                self.db.query(EIGRPNeighbor)
                .filter(
                    EIGRPNeighbor.device_id == device.id,
                    EIGRPNeighbor.neighbor_ip == neighbor_ip,
                )
                .first()
            )

            if not neighbor:
                neighbor = EIGRPNeighbor(device_id=device.id)

            neighbor.neighbor_ip = neighbor_ip
            neighbor.autonomous_system = data.get("autonomous_system", 0)
            neighbor.uptime = data.get("uptime", 0)
            neighbor.hold_time = data.get("hold_time", 15)
            neighbor.srtt = data.get("srtt", 0)
            neighbor.rto = data.get("rto", 0)
            neighbor.queue_count = data.get("queue_count", 0)

            self.db.add(neighbor)
            count += 1

        self.db.commit()
        return count

    # ============================================
    # Combined Method
    # ============================================

    def poll_all_routing_protocols(self, device: Device) -> Dict[str, Any]:
        """
        Poll all routing protocols from a device.

        Returns combined routing data.
        """
        return {
            "ospf": {
                "neighbors": self.poll_ospf_neighbors(device),
                "processes": self.poll_ospf_processes(device),
            },
            "bgp": {
                "neighbors": self.poll_bgp_neighbors(device),
            },
            "eigrp": {
                "neighbors": self.poll_eigrp_neighbors(device),
            },
        }

    def save_all_routing_data(
        self,
        device: Device,
        routing_data: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Save all routing protocol data to database.

        Returns counts of saved items per protocol.
        """
        return {
            "ospf_neighbors": self.save_ospf_neighbors(
                device, routing_data.get("ospf", {}).get("neighbors", [])
            ),
            "bgp_neighbors": self.save_bgp_neighbors(
                device, routing_data.get("bgp", {}).get("neighbors", [])
            ),
            "eigrp_neighbors": self.save_eigrp_neighbors(
                device, routing_data.get("eigrp", {}).get("neighbors", [])
            ),
        }


# Factory function
def get_routing_service(db: Session) -> RoutingService:
    """Get routing service instance."""
    return RoutingService(db)
