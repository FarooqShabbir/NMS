"""Core SNMP service for device polling."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

from ..core.config import settings
from ..utils.oid_mappings import (
    SYS_DESCR,
    SYS_UPTIME,
    IF_OPER_STATUS,
    IF_ADMIN_STATUS,
    IF_IN_OCTETS,
    IF_OUT_OCTETS,
    IF_IN_ERRORS,
    IF_OUT_ERRORS,
    IF_IN_DISCARDS,
    IF_OUT_DISCARDS,
    IF_SPEED,
    IF_NAME,
    IF_DESCR,
    get_if_status_name,
    CISCO_CPU_5SEC,
    CISCO_MEMORY_USED,
    CISCO_MEMORY_FREE,
    MEM_POOL_USED,
    MEM_POOL_FREE,
)
from ..models.device import SNMPVersion

SNMP_AVAILABLE = True
SNMP_IMPORT_ERROR: Optional[Exception] = None

try:
    from pysnmp.hlapi import (
        SnmpEngine,
        CommunityData,
        UdpTransportTarget,
        ContextData,
        UsmUserData,
        usmHMACMD5AuthProtocol,
        usmHMACSHAAuthProtocol,
        usmHMAC128SHA224AuthProtocol,
        usmNoAuthProtocol,
        usmDESPrivProtocol,
        usmAesCfb128Protocol,
        usmAesCfb192Protocol,
        usmAesCfb256Protocol,
        usmNoPrivProtocol,
        getCmd,
        bulkCmd,
        ObjectType,
        ObjectIdentity,
    )
    from pysnmp.proto.rfc1902 import Integer, OctetString, Counter32, Counter64, Gauge32, TimeTicks
except Exception as exc:  # pragma: no cover - runtime-dependent import behavior
    SNMP_AVAILABLE = False
    SNMP_IMPORT_ERROR = exc


class SNMPError(Exception):
    """SNMP operation error."""
    pass


class SNMPService:
    """SNMP service for polling network devices."""

    def __init__(self):
        self.snmp_engine = SnmpEngine() if SNMP_AVAILABLE else None
        self.timeout = settings.SNMP_TIMEOUT
        self.retries = settings.SNMP_RETRIES

    def _require_snmp(self):
        """Ensure SNMP runtime dependencies are available before use."""
        if not SNMP_AVAILABLE or self.snmp_engine is None:
            raise SNMPError(
                f"SNMP dependencies are unavailable in this runtime: {SNMP_IMPORT_ERROR}"
            )

    def _get_auth_data(
        self,
        ip: str,
        version: SNMPVersion,
        community: Optional[str] = None,
        v3_username: Optional[str] = None,
        v3_auth_protocol: Optional[str] = None,
        v3_auth_password: Optional[str] = None,
        v3_priv_protocol: Optional[str] = None,
        v3_priv_password: Optional[str] = None,
    ) -> CommunityData | UsmUserData:
        """Get SNMP authentication data based on version."""
        if version == SNMPVersion.V3:
            # SNMPv3 authentication
            auth_protocol_map = {
                "MD5": usmHMACMD5AuthProtocol,
                "SHA": usmHMACSHAAuthProtocol,
                "SHA256": usmHMAC128SHA224AuthProtocol,
            }
            priv_protocol_map = {
                "DES": usmDESPrivProtocol,
                "AES": usmAesCfb128Protocol,
                "AES192": usmAesCfb192Protocol,
                "AES256": usmAesCfb256Protocol,
            }

            auth_proto = auth_protocol_map.get((v3_auth_protocol or "").upper(), usmNoAuthProtocol)
            priv_proto = priv_protocol_map.get((v3_priv_protocol or "").upper(), usmNoPrivProtocol)

            return UsmUserData(
                v3_username,
                authKey=v3_auth_password or "",
                privKey=v3_priv_password or "",
                authProtocol=auth_proto,
                privProtocol=priv_proto,
            )
        else:
            # SNMPv1 or v2c
            return CommunityData(community or "public")

    def _get_transport_target(self, ip: str, port: int = 161) -> UdpTransportTarget:
        """Get SNMP transport target."""
        return UdpTransportTarget(
            (ip, port),
            timeout=self.timeout,
            retries=self.retries,
        )

    def _get_context_data(self) -> ContextData:
        """Get SNMP context data."""
        return ContextData()

    @contextmanager
    def _handle_snmp_errors(self, ip: str):
        """Context manager for handling SNMP errors."""
        try:
            yield
        except Exception as e:
            raise SNMPError(f"SNMP error for {ip}: {str(e)}")

    def get_value(self, oid: str, device: "Device") -> Any:
        """
        Get a single SNMP value.

        Args:
            oid: OID to query
            device: Device model instance

        Returns:
            The value or None if error
        """
        self._require_snmp()

        with self._handle_snmp_errors(device.ip_address):
            auth_data = self._get_auth_data(
                device.ip_address,
                device.snmp_version,
                device.snmp_community,
                device.snmp_v3_username,
                device.snmp_v3_auth_protocol,
                device.snmp_v3_auth_password,
                device.snmp_v3_priv_protocol,
                device.snmp_v3_priv_password,
            )

            iterator = getCmd(
                self.snmp_engine,
                auth_data,
                self._get_transport_target(device.ip_address),
                self._get_context_data(),
                ObjectType(ObjectIdentity(oid)),
                lookupMib=False,
            )

            for response in iterator:
                error_indication, error_status, error_index, var_binds = response

                if error_indication:
                    raise SNMPError(f"{device.ip_address}: {error_indication}")
                elif error_status:
                    raise SNMPError(f"{device.ip_address}: {error_status.prettyPrint()}")
                else:
                    for var_bind in var_binds:
                        return self._convert_value(var_bind[1])

        return None

    def get_bulk(
        self,
        oids: List[str],
        device: "Device",
        max_repetitions: int = 10,
    ) -> Dict[str, Any]:
        """
        Get multiple SNMP values using bulk walk.

        Args:
            oids: List of OIDs to query
            device: Device model instance
            max_repetitions: Max repetitions for bulk requests

        Returns:
            Dict mapping OID to value
        """
        self._require_snmp()

        results = {}

        with self._handle_snmp_errors(device.ip_address):
            auth_data = self._get_auth_data(
                device.ip_address,
                device.snmp_version,
                device.snmp_community,
                device.snmp_v3_username,
                device.snmp_v3_auth_protocol,
                device.snmp_v3_auth_password,
                device.snmp_v3_priv_protocol,
                device.snmp_v3_priv_password,
            )

            for oid in oids:
                iterator = bulkCmd(
                    self.snmp_engine,
                    auth_data,
                    self._get_transport_target(device.ip_address),
                    self._get_context_data(),
                    0,  # non-repeaters
                    max_repetitions,
                    ObjectType(ObjectIdentity(oid)),
                    lookupMib=False,
                    lexicographicMode=False,
                )

                for response in iterator:
                    error_indication, error_status, error_index, var_binds = response

                    if error_indication:
                        raise SNMPError(f"{device.ip_address}: {error_indication}")
                    elif error_status:
                        raise SNMPError(f"{device.ip_address}: {error_status.prettyPrint()}")
                    else:
                        for var_bind in var_binds:
                            oid_str = str(var_bind[0])
                            results[oid_str] = self._convert_value(var_bind[1])

        return results

    def walk(self, base_oid: str, device: "Device") -> Dict[str, Any]:
        """
        Walk an OID subtree.

        Args:
            base_oid: Base OID to walk
            device: Device model instance

        Returns:
            Dict mapping OID suffix to value
        """
        self._require_snmp()

        results = {}
        base_oid = base_oid.rstrip(".")

        with self._handle_snmp_errors(device.ip_address):
            auth_data = self._get_auth_data(
                device.ip_address,
                device.snmp_version,
                device.snmp_community,
                device.snmp_v3_username,
                device.snmp_v3_auth_protocol,
                device.snmp_v3_auth_password,
                device.snmp_v3_priv_protocol,
                device.snmp_v3_priv_password,
            )

            iterator = bulkCmd(
                self.snmp_engine,
                auth_data,
                self._get_transport_target(device.ip_address),
                self._get_context_data(),
                0,
                10,
                ObjectType(ObjectIdentity(base_oid)),
                lookupMib=False,
            )

            for response in iterator:
                error_indication, error_status, error_index, var_binds = response

                if error_indication:
                    break
                elif error_status:
                    break
                else:
                    for var_bind in var_binds:
                        oid_str = str(var_bind[0])
                        # Check if still within subtree
                        if not oid_str.startswith(base_oid + "."):
                            continue
                        # Get the suffix
                        suffix = oid_str[len(base_oid) + 1:]
                        results[suffix] = self._convert_value(var_bind[1])

        return results

    def _convert_value(self, value) -> Any:
        """Convert SNMP value to Python type."""
        if value is None:
            return None

        if not SNMP_AVAILABLE:
            return str(value)

        if isinstance(value, Integer):
            return int(value)
        elif isinstance(value, Gauge32):
            return int(value)
        elif isinstance(value, Counter32):
            return int(value)
        elif isinstance(value, Counter64):
            return int(value)
        elif isinstance(value, TimeTicks):
            return int(value)
        elif isinstance(value, OctetString):
            # Try to decode as string
            try:
                return str(value)
            except Exception:
                return value.hex()
        else:
            return str(value)

    def test_connection(self, device: "Device") -> Tuple[bool, str]:
        """
        Test SNMP connection to a device.

        Returns:
            Tuple of (success, message)
        """
        try:
            self._require_snmp()
            # Try to get system description
            result = self.get_value(SYS_DESCR, device)
            if result:
                return True, f"Connected: {result[:50]}"
            return False, "No response from device"
        except SNMPError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Error: {str(e)}"


# Singleton instance
snmp_service = SNMPService()
