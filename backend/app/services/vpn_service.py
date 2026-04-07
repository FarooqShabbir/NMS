"""VPN and DMVPN service - polling VPN tunnel status via SNMP."""
import asyncio
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.vpn import VPNTunnel, NHRPCache, IPSecSA, TunnelStatus, IKEPhase1Status, IPSecStatus
from ..utils.oid_mappings import (
    # IPSec
    CISCO_IPSEC_TUNNEL_TABLE,
    CISCO_IPSEC_TUNNEL_NAME,
    CISCO_IPSEC_TUNNEL_LOCAL_ADDR,
    CISCO_IPSEC_TUNNEL_REMOTE_ADDR,
    CISCO_IPSEC_TUNNEL_STATUS,
    CISCO_IPSEC_SA_TABLE,
    CISCO_IPSEC_SA_STATUS,
    CISCO_IPSEC_SA_ENCRYPT_ALG,
    CISCO_IPSEC_SA_BYTES_ENCRYPTED,
    CISCO_IPSEC_SA_BYTES_DECRYPTED,
    CISCO_IPSEC_SA_DROP_PKTS,
    # GRE
    GRE_TUNNEL_TABLE,
    GRE_TUNNEL_SOURCE,
    GRE_TUNNEL_DESTINATION,
    GRE_TUNNEL_STATUS,
    # DMVPN / NHRP
    NHRP_CACHE_TABLE,
    NHRP_CACHE_PROTOCOL_ADDR,
    NHRP_CACHE_NBMA_ADDR,
    NHRP_CACHE_TYPE,
    NHRP_CACHE_REMAIN_TIME,
    CISCO_DMVPN_TUNNEL_TABLE,
    CISCO_DMVPN_TUNNEL_TYPE,
)
from .snmp_service import snmp_service


class VPNService:
    """Service for polling VPN and DMVPN information."""

    def __init__(self, db: Session):
        self.db = db
        self.snmp = snmp_service

    # ============================================
    # IPSec Tunnel Methods
    # ============================================

    def poll_ipsec_tunnels(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll IPSec tunnel information from device.

        Returns list of IPSec tunnel data.
        """
        tunnels = []

        try:
            # Walk IPSec tunnel table
            tunnel_data = self.snmp.walk(CISCO_IPSEC_TUNNEL_TABLE, device)

            # Group data by tunnel
            tunnel_entries = {}

            for suffix, value in tunnel_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                # First part is typically the tunnel index
                tunnel_index = parts[0]
                column = parts[1] if len(parts) > 1 else ""

                if tunnel_index not in tunnel_entries:
                    tunnel_entries[tunnel_index] = {
                        "tunnel_type": "ipsec",
                        "ike_version": 2,
                    }

                # Map column to value
                if column == "2":  # Tunnel name
                    tunnel_entries[tunnel_index]["tunnel_name"] = str(value)
                elif column == "3":  # Local address
                    tunnel_entries[tunnel_index]["local_endpoint"] = str(value)
                elif column == "4":  # Remote address
                    tunnel_entries[tunnel_index]["remote_endpoint"] = str(value)
                elif column == "5":  # Status
                    status_val = int(value)
                    if status_val == 1:
                        tunnel_entries[tunnel_index]["status"] = TunnelStatus.UP
                        tunnel_entries[tunnel_index]["ike_phase1_status"] = IKEPhase1Status.ACTIVE
                        tunnel_entries[tunnel_index]["ipsec_status"] = IPSecStatus.ACTIVE
                    else:
                        tunnel_entries[tunnel_index]["status"] = TunnelStatus.DOWN
                        tunnel_entries[tunnel_index]["ike_phase1_status"] = IKEPhase1Status.INACTIVE
                        tunnel_entries[tunnel_index]["ipsec_status"] = IPSecStatus.INACTIVE

            # Get IPSec SA statistics
            try:
                sa_data = self.snmp.walk(CISCO_IPSEC_SA_TABLE, device)
                sa_stats = {}

                for suffix, value in sa_data.items():
                    parts = suffix.split(".")
                    if len(parts) < 2:
                        continue
                    sa_index = parts[0]
                    column = parts[1] if len(parts) > 1 else ""

                    if sa_index not in sa_stats:
                        sa_stats[sa_index] = {}

                    if column == "15":  # Bytes encrypted
                        sa_stats[sa_index]["bytes_encrypted"] = int(value)
                    elif column == "20":  # Bytes decrypted
                        sa_stats[sa_index]["bytes_decrypted"] = int(value)
                    elif column == "18":  # Drop packets
                        sa_stats[sa_index]["packets_dropped"] = int(value)

                # Aggregate SA stats to tunnels (simplified mapping)
                if sa_stats:
                    total_encrypted = sum(s.get("bytes_encrypted", 0) for s in sa_stats.values())
                    total_decrypted = sum(s.get("bytes_decrypted", 0) for s in sa_stats.values())
                    total_dropped = sum(s.get("packets_dropped", 0) for s in sa_stats.values())

                    for tunnel in tunnel_entries.values():
                        tunnel["bytes_encrypted"] = total_encrypted
                        tunnel["bytes_decrypted"] = total_decrypted
                        tunnel["packets_dropped"] = total_dropped

            except Exception:
                pass

            tunnels = list(tunnel_entries.values())

        except Exception as e:
            # IPSec might not be enabled
            pass

        return tunnels

    # ============================================
    # GRE Tunnel Methods
    # ============================================

    def poll_gre_tunnels(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll GRE tunnel information from device.

        Returns list of GRE tunnel data.
        """
        tunnels = []

        try:
            # Walk GRE tunnel table
            tunnel_data = self.snmp.walk(GRE_TUNNEL_TABLE, device)

            # Group data by tunnel
            tunnel_entries = {}

            for suffix, value in tunnel_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                # Interface index
                if_index = parts[0]
                column = parts[1] if len(parts) > 1 else ""

                if if_index not in tunnel_entries:
                    tunnel_entries[if_index] = {
                        "tunnel_type": "gre",
                    }

                # Map column to value
                if column == "2":  # Source
                    tunnel_entries[if_index]["local_endpoint"] = str(value)
                elif column == "3":  # Destination
                    tunnel_entries[if_index]["remote_endpoint"] = str(value)
                elif column == "4":  # Status
                    status_val = int(value)
                    tunnel_entries[if_index]["status"] = (
                        TunnelStatus.UP if status_val == 1 else TunnelStatus.DOWN
                    )

            tunnels = list(tunnel_entries.values())

        except Exception:
            # GRE might not be enabled
            pass

        return tunnels

    # ============================================
    # DMVPN / NHRP Methods
    # ============================================

    def poll_dmvpn_tunnels(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll DMVPN tunnel information from device.

        Returns list of DMVPN tunnel data.
        """
        tunnels = []

        try:
            # Walk DMVPN tunnel table
            tunnel_data = self.snmp.walk(CISCO_DMVPN_TUNNEL_TABLE, device)

            # Group data by tunnel
            tunnel_entries = {}

            for suffix, value in tunnel_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                if_index = parts[0]
                column = parts[1] if len(parts) > 1 else ""

                if if_index not in tunnel_entries:
                    tunnel_entries[if_index] = {
                        "tunnel_type": "dmvpn",
                    }

                # Map column to value
                if column == "2":  # Tunnel type (hub=1, spoke=2)
                    tunnel_type = int(value)
                    tunnel_entries[if_index]["nhrp_peer_type"] = (
                        "hub" if tunnel_type == 1 else "spoke"
                    )

            # Get NHRP cache for spoke count
            try:
                nhrp_cache = self.poll_nhrp_cache(device)
                if tunnel_entries:
                    # For hub: count unique spokes in NHRP cache
                    # For spoke: check if hub is reachable
                    for tunnel in tunnel_entries.values():
                        if tunnel.get("nhrp_peer_type") == "hub":
                            tunnel["spoke_count"] = len(nhrp_cache)
                        else:
                            tunnel["hub_reachable"] = any(
                                entry.get("entry_type") == "static" for entry in nhrp_cache
                            )
            except Exception:
                pass

            tunnels = list(tunnel_entries.values())

        except Exception:
            # DMVPN might not be enabled
            pass

        return tunnels

    def poll_nhrp_cache(self, device: Device) -> List[Dict[str, Any]]:
        """
        Poll NHRP cache entries (for DMVPN).

        Returns list of NHRP cache entries.
        """
        cache_entries = []

        try:
            # Walk NHRP cache table
            cache_data = self.snmp.walk(NHRP_CACHE_TABLE, device)

            # Group data by entry
            entry_map = {}

            for suffix, value in cache_data.items():
                parts = suffix.split(".")
                if len(parts) < 2:
                    continue

                # Index typically includes interface and entry index
                entry_index = ".".join(parts[:2]) if len(parts) > 2 else parts[0]
                column = parts[-1] if parts else ""

                if entry_index not in entry_map:
                    entry_map[entry_index] = {}

                # Map column to value
                if column == "2":  # Protocol address
                    entry_map[entry_index]["protocol_ip"] = str(value)
                elif column == "3":  # NBMA address
                    entry_map[entry_index]["nbma_ip"] = str(value)
                elif column == "4":  # Entry type (1=dynamic, 2=static)
                    entry_type = int(value)
                    entry_map[entry_index]["entry_type"] = "dynamic" if entry_type == 1 else "static"
                elif column == "6":  # Remaining time
                    entry_map[entry_index]["remaining_time"] = int(value)

            cache_entries = list(entry_map.values())

        except Exception:
            # NHRP might not be enabled
            pass

        return cache_entries

    # ============================================
    # Save Methods
    # ============================================

    def save_vpn_tunnels(
        self,
        device: Device,
        tunnel_data: List[Dict[str, Any]],
    ) -> int:
        """
        Save VPN tunnel data to database.

        Returns number of tunnels saved.
        """
        count = 0

        for data in tunnel_data:
            tunnel_name = data.get("tunnel_name") or data.get("local_endpoint", "")
            if not tunnel_name:
                continue

            tunnel = (
                self.db.query(VPNTunnel)
                .filter(
                    VPNTunnel.device_id == device.id,
                    VPNTunnel.tunnel_name == tunnel_name,
                )
                .first()
            )

            if not tunnel:
                tunnel = VPNTunnel(device_id=device.id)

            tunnel.tunnel_name = tunnel_name
            tunnel.tunnel_type = data.get("tunnel_type", "ipsec")
            tunnel.status = data.get("status", TunnelStatus.UNKNOWN)
            tunnel.local_endpoint = data.get("local_endpoint")
            tunnel.remote_endpoint = data.get("remote_endpoint")
            tunnel.ike_phase1_status = data.get("ike_phase1_status")
            tunnel.ipsec_status = data.get("ipsec_status")
            tunnel.encryption_algorithm = data.get("encryption_algorithm")
            tunnel.bytes_encrypted = data.get("bytes_encrypted", 0)
            tunnel.bytes_decrypted = data.get("bytes_decrypted", 0)
            tunnel.packets_dropped = data.get("packets_dropped", 0)
            tunnel.nhrp_peer_type = data.get("nhrp_peer_type")

            self.db.add(tunnel)
            count += 1

        self.db.commit()
        return count

    def save_nhrp_cache(
        self,
        device: Device,
        cache_data: List[Dict[str, Any]],
    ) -> int:
        """
        Save NHRP cache data to database.

        Returns number of entries saved.
        """
        count = 0

        for data in cache_data:
            protocol_ip = data.get("protocol_ip")
            if not protocol_ip:
                continue

            entry = (
                self.db.query(NHRPCache)
                .filter(
                    NHRPCache.device_id == device.id,
                    NHRPCache.protocol_ip == protocol_ip,
                )
                .first()
            )

            if not entry:
                entry = NHRPCache(device_id=device.id)

            entry.protocol_ip = protocol_ip
            entry.nbma_ip = data.get("nbma_ip", "")
            entry.entry_type = data.get("entry_type", "dynamic")
            entry.remaining_time = data.get("remaining_time", 0)

            self.db.add(entry)
            count += 1

        self.db.commit()
        return count

    # ============================================
    # Combined Method
    # ============================================

    def poll_all_vpn_data(self, device: Device) -> Dict[str, Any]:
        """
        Poll all VPN-related data from a device.

        Returns combined VPN data.
        """
        ipsec_tunnels = self.poll_ipsec_tunnels(device)
        gre_tunnels = self.poll_gre_tunnels(device)
        dmvpn_tunnels = self.poll_dmvpn_tunnels(device)
        nhrp_cache = self.poll_nhrp_cache(device)

        # Combine all tunnels
        all_tunnels = ipsec_tunnels + gre_tunnels + dmvpn_tunnels

        return {
            "tunnels": all_tunnels,
            "ipsec_tunnels": ipsec_tunnels,
            "gre_tunnels": gre_tunnels,
            "dmvpn_tunnels": dmvpn_tunnels,
            "nhrp_cache": nhrp_cache,
        }

    def save_all_vpn_data(
        self,
        device: Device,
        vpn_data: Dict[str, Any],
    ) -> Dict[str, int]:
        """
        Save all VPN data to database.

        Returns counts of saved items.
        """
        return {
            "tunnels": self.save_vpn_tunnels(device, vpn_data.get("tunnels", [])),
            "nhrp_cache": self.save_nhrp_cache(device, vpn_data.get("nhrp_cache", [])),
        }


# Factory function
def get_vpn_service(db: Session) -> VPNService:
    """Get VPN service instance."""
    return VPNService(db)
