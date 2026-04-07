"""SNMP OID mappings for various vendors and metrics."""

# Standard MIB-2 OIDs (RFC 1213)
MIB2 = "1.3.6.1.2.1"

# System information
SYSTEM_OID = f"{MIB2}.1"
SYS_DESCR = f"{SYSTEM_OID}.1.0"
SYS_UPTIME = f"{SYSTEM_OID}.3.0"
SYS_NAME = f"{SYSTEM_OID}.5.0"
SYS_LOCATION = f"{SYSTEM_OID}.6.0"

# Interfaces MIB (IF-MIB - RFC 2863)
IF_MIB = f"{MIB2}.31.1.1"
IF_NUMBER = f"{MIB2}.2.2.0"

# Interface table
IF_ENTRY = f"{IF_MIB}.1"
IF_INDEX = f"{IF_ENTRY}.1"
IF_DESCR = f"{IF_ENTRY}.2"
IF_TYPE = f"{IF_ENTRY}.3"
IF_MTU = f"{IF_ENTRY}.4"
IF_SPEED = f"{IF_ENTRY}.5"
IF_PHYS_ADDRESS = f"{IF_ENTRY}.6"
IF_ADMIN_STATUS = f"{IF_ENTRY}.7"
IF_OPER_STATUS = f"{IF_ENTRY}.8"
IF_LAST_CHANGE = f"{IF_ENTRY}.9"
IF_IN_OCTETS = f"{IF_ENTRY}.10"
IF_IN_UCAST_PKTS = f"{IF_ENTRY}.11"
IF_IN_ERRORS = f"{IF_ENTRY}.14"
IF_IN_DISCARDS = f"{IF_ENTRY}.13"
IF_OUT_OCTETS = f"{IF_ENTRY}.16"
IF_OUT_UCAST_PKTS = f"{IF_ENTRY}.17"
IF_OUT_ERRORS = f"{IF_ENTRY}.20"
IF_OUT_DISCARDS = f"{IF_ENTRY}.19"

# Interface names (IF-MIB extension)
IF_NAME = f"{IF_MIB}.1.1"
IF_ALIAS = f"{IF_MIB}.1.18"

# Host Resources MIB (for CPU/Memory)
HOST_RESOURCES_MIB = "1.3.6.1.2.1.25"
HR_DEVICE = f"{HOST_RESOURCES_MIB}.3"
HR_STORAGE = f"{HOST_RESOURCES_MIB}.6"
HR_PROCESS = f"{HOST_RESOURCES_MIB}.7"

# CPU usage (various vendors)
# Cisco
CISCO_CPU_OID = "1.3.6.1.4.1.9.9.109.1.1.1.1"
CISCO_CPU_5SEC = f"{CISCO_CPU_OID}.2"  # 5 second avg
CISCO_CPU_1MIN = f"{CISCO_CPU_OID}.3"  # 1 minute avg
CISCO_CPU_5MIN = f"{CISCO_CPU_OID}.4"  # 5 minute avg

# Generic CPU (from HOST-RESOURCES-MIB)
HR_PROCESSOR_LOAD = f"{HOST_RESOURCES_MIB}.3.3.1.2"  # Processor load
HR_PROCESSOR_FRUITION = f"{HOST_RESOURCES_MIB}.3.3.1.2"  # Processor utilization

# Memory OIDs
# Cisco
CISCO_MEMORY_OID = "1.3.6.1.4.1.9.9.48.1.1.1"
CISCO_MEMORY_USED = f"{CISCO_MEMORY_OID}.5"  # ciscoMemoryPoolUsed
CISCO_MEMORY_FREE = f"{CISCO_MEMORY_OID}.6"  # ciscoMemoryPoolFree

# HOST-RESOURCES-MIB memory
HR_STORAGE_USED = f"{HR_STORAGE}.2.1.6"  # hrStorageUsed
HR_STORAGE_SIZE = f"{HR_STORAGE}.2.1.3"  # hrStorageSize
HR_STORAGE_ALLOC_UNITS = f"{HR_STORAGE}.2.1.4"  # hrStorageAllocationUnits

# Standard memory pool (used by many vendors)
MEM_POOL_USED = "1.3.6.1.4.1.2021.4.6.0"  # memTotalReal
MEM_POOL_FREE = "1.3.6.1.4.1.2021.4.11.0"  # memAvailReal

# Disk/Storage OIDs
HR_STORAGE_DESCRIPTION = f"{HR_STORAGE}.2.1.2"
HR_STORAGE_CAPACITY = f"{HR_STORAGE}.2.1.3"
HR_STORAGE_USED_SPACE = f"{HR_STORAGE}.2.1.6"

# Temperature OIDs (vendor specific)
# Cisco
CISCO_TEMP_OID = "1.3.6.1.4.1.9.9.13.1.3.1.3"  # envmonTemperatureValue

# Fan Status OIDs
# Cisco
CISCO_FAN_OID = "1.3.6.1.4.1.9.9.13.1.4.1.3"  # envmonFanStatus

# Power Supply OIDs
# Cisco
CISCO_POWER_OID = "1.3.6.1.4.1.9.9.13.1.5.1.3"  # envmonPowerStatus

# ============================================
# ROUTING PROTOCOL OIDs
# ============================================

# OSPF MIB (RFC 1850 - OSPF-MIB)
OSPF_MIB = "1.3.6.1.2.1.14"

# OSPF General
OSPF_ROUTER_ID = f"{OSPF_MIB}.1.0"
OSPF_ADMIN_STATUS = f"{OSPF_MIB}.2.0"
OSPF_VERSION_NUMBER = f"{OSPF_MIB}.3.0"
OSPF_AREA_COUNT = f"{OSPF_MIB}.18.0"

# OSPF Neighbor Table
OSPF_NEIGHBOR_TABLE = f"{OSPF_MIB}.10"
OSPF_NEIGHBOR_ENTRY = f"{OSPF_NEIGHBOR_TABLE}.1"
OSPF_NEIGHBOR_IP = f"{OSPF_NEIGHBOR_ENTRY}.1"  # ospfNbrIpAddr
OSPF_NEIGHBOR_IF_INDEX = f"{OSPF_NEIGHBOR_ENTRY}.2"  # ospfNbrAddressLessIndex
OSPF_NEIGHBOR_ROUTER_ID = f"{OSPF_NEIGHBOR_ENTRY}.3"  # ospfNbrRtrId
OSPF_NEIGHBOR_PRIORITY = f"{OSPF_NEIGHBOR_ENTRY}.4"  # ospfNbrPriority
OSPF_NEIGHBOR_STATE = f"{OSPF_NEIGHBOR_ENTRY}.6"  # ospfNbrState (1=Down, 8=Full)
OSPF_NEIGHBOR_EVENTS = f"{OSPF_NEIGHBOR_ENTRY}.7"  # ospfNbrEvents
OSPF_NEIGHBOR_RETRANS_QUEUE = f"{OSPF_NEIGHBOR_ENTRY}.11"  # ospfNbrRxBadList
OSPF_NEIGHBOR_HELLO_INTERVAL = f"{OSPF_NEIGHBOR_ENTRY}.13"  # ospfNbrHelloInterval
OSPF_NEIGHBOR_DEAD_INTERVAL = f"{OSPF_NEIGHBOR_ENTRY}.14"  # ospfNbrRtrDeadInterval

# OSPF Area Table
OSPF_AREA_TABLE = f"{OSPF_MIB}.3"
OSPF_AREA_ENTRY = f"{OSPF_AREA_TABLE}.1"
OSPF_AREA_ID = f"{OSPF_AREA_ENTRY}.1"
OSPF_AREA_TYPE = f"{OSPF_AREA_ENTRY}.5"  # ospfAreaType

# OSPF Interface Table
OSPF_IF_TABLE = f"{OSPF_MIB}.4"
OSPF_IF_ENTRY = f"{OSPF_IF_TABLE}.1"
OSPF_IF_IP_ADDR = f"{OSPF_IF_ENTRY}.1"
OSPF_IF_AREA_ID = f"{OSPF_IF_ENTRY}.2"
OSPF_IF_STATE = f"{OSPF_IF_ENTRY}.5"  # ospfIfState
OSPF_IF_ADMIN_STATUS = f"{OSPF_IF_ENTRY}.6"

# BGP MIB (RFC 1657 / RFC 4273 - BGP4-MIB)
BGP_MIB = "1.3.6.1.2.1.15"

# BGP General (RFC 1657)
BGP_VERSION = f"{BGP_MIB}.1.0"
BGP_LOCAL_AS = f"{BGP_MIB}.2.0"

# BGP Peer Table (RFC 1657)
BGP_PEER_TABLE = f"{BGP_MIB}.3"
BGP_PEER_ENTRY = f"{BGP_PEER_TABLE}.1"
BGP_PEER_IP = f"{BGP_PEER_ENTRY}.1"  # bgpPeerIdentifier
BGP_PEER_STATE = f"{BGP_PEER_ENTRY}.2"  # bgpPeerState (1=Idle, 6=Established)
BGP_PEER_ADMIN_STATUS = f"{BGP_PEER_ENTRY}.3"  # bgpPeerAdminStatus
BGP_PEER_LOCAL_AS = f"{BGP_PEER_ENTRY}.14"  # bgpPeerLocalAs
BGP_PEER_REMOTE_AS = f"{BGP_PEER_ENTRY}.10"  # bgpPeerRemoteAs
BGP_PEER_UPTIME = f"{BGP_PEER_ENTRY}.13"  # bgpPeerFsmEstablishedTime
BGP_PEER_IN_UPDATES = f"{BGP_PEER_ENTRY}.5"  # bgpPeerInUpdates
BGP_PEER_OUT_UPDATES = f"{BGP_PEER_ENTRY}.6"  # bgpPeerOutUpdates
BGP_PEER_IN_TOTALMESSAGES = f"{BGP_PEER_ENTRY}.7"  # bgpPeerInTotalMessages
BGP_PEER_OUT_TOTALMESSAGES = f"{BGP_PEER_ENTRY}.8"  # bgpPeerOutTotalMessages

# BGP-4 MIB (RFC 4273) - Prefix counts
BGP4_MIB = "1.3.6.1.2.1.15.3"
BGP4_PREFIX_TABLE = f"{BGP4_MIB}.1"
BGP4_PREFIX_ENTRY = f"{BGP4_PREFIX_TABLE}.1"
BGP4_PREFIX_IP = f"{BGP4_PREFIX_ENTRY}.1"
BGP4_PREFIX_AFI = f"{BGP4_PREFIX_ENTRY}.2"
BGP4_PREFIX_SAFI = f"{BGP4_PREFIX_ENTRY}.3"
BGP4_PREFIX_COUNT = f"{BGP4_PREFIX_ENTRY}.4"  # Number of prefixes

# CISCO-BGP4-MIB (more detailed info)
CISCO_BGP_MIB = "1.3.6.1.4.1.9.9.187"
CBGP_PEER_TABLE = f"{CISCO_BGP_MIB}.1.2.2.1"
CBGP_PEER_PREFIX_RECEIVED = "1.3.6.1.4.1.9.9.187.1.2.2.1.20"  # cbgpPrefixAdminReceived
CBGP_PEER_PREFIX_SENT = "1.3.6.1.4.1.9.9.187.1.2.2.1.21"  # cbgpPrefixAdminSent

# EIGRP MIB (CISCO-EIGRP-MIB)
CISCO_EIGRP_MIB = "1.3.6.1.4.1.9.9.91"

# EIGRP General
EIGRP_GENERAL = f"{CISCO_EIGRP_MIB}.1.1"
EIGRP_ASN_TABLE = f"{CISCO_EIGRP_MIB}.1.2"
EIGRP_ASN_ENTRY = f"{EIGRP_ASN_TABLE}.1"
EIGRP_ASN = f"{EIGRP_ASN_ENTRY}.1"  # ciscoEigrpASNumber

# EIGRP Neighbor Table
EIGRP_NEIGHBOR_TABLE = f"{CISCO_EIGRP_MIB}.1.3"
EIGRP_NEIGHBOR_ENTRY = f"{EIGRP_NEIGHBOR_TABLE}.1"
EIGRP_NEIGHBOR_IP = f"{EIGRP_NEIGHBOR_ENTRY}.2"  # ciscoEigrpNeighborIpAddress
EIGRP_NEIGHBOR_IF_INDEX = f"{EIGRP_NEIGHBOR_ENTRY}.3"  # ciscoEigrpNeighborIfIndex
EIGRP_NEIGHBOR_UPTIME = f"{EIGRP_NEIGHBOR_ENTRY}.5"  # ciscoEigrpNeighborUpTime
EIGRP_NEIGHBOR_HOLD_TIME = f"{EIGRP_NEIGHBOR_ENTRY}.6"  # ciscoEigrpNeighborHoldTime
EIGRP_NEIGHBOR_SRTT = f"{EIGRP_NEIGHBOR_ENTRY}.8"  # ciscoEigrpNeighborSrtt
EIGRP_NEIGHBOR_RTO = f"{EIGRP_NEIGHBOR_ENTRY}.9"  # ciscoEigrpNeighborRto
EIGRP_NEIGHBOR_QUEUE_COUNT = f"{EIGRP_NEIGHBOR_ENTRY}.11"  # ciscoEigrpNeighborQCnt

# EIGRP Topology Table
EIGRP_TOPO_TABLE = f"{CISCO_EIGRP_MIB}.1.4"
EIGRP_TOPO_ENTRY = f"{EIGRP_TOPO_TABLE}.1"
EIGRP_TOPO_DESTINATION = f"{EIGRP_TOPO_ENTRY}.2"  # ciscoEigrpTbDestinationNetwork
EIGRP_TOPO_SUCCESSOR_COUNT = f"{EIGRP_TOPO_ENTRY}.6"  # ciscoEigrpTbSucrCount

# ============================================
# VPN OIDs
# ============================================

# IPSec MIB (RFC 4181 - IPSec-SPD-MIB, CISCO-IPSEC-MIB)
CISCO_IPSEC_MIB = "1.3.6.1.4.1.9.9.171"

# IPSec Tunnel Endpoints
CISCO_IPSEC_TUNNEL_TABLE = f"{CISCO_IPSEC_MIB}.2.1"
CISCO_IPSEC_TUNNEL_ENTRY = f"{CISCO_IPSEC_TUNNEL_TABLE}.1"
CISCO_IPSEC_TUNNEL_NAME = f"{CISCO_IPSEC_TUNNEL_ENTRY}.2"  # cikeTunnelName
CISCO_IPSEC_TUNNEL_LOCAL_ADDR = f"{CISCO_IPSEC_TUNNEL_ENTRY}.3"  # cikeTunnelLocalAddr
CISCO_IPSEC_TUNNEL_REMOTE_ADDR = f"{CISCO_IPSEC_TUNNEL_ENTRY}.4"  # cikeTunnelRemoteAddr
CISCO_IPSEC_TUNNEL_STATUS = f"{CISCO_IPSEC_TUNNEL_ENTRY}.5"  # cikeTunnelStatus

# IPSec SA
CISCO_IPSEC_SA_TABLE = f"{CISCO_IPSEC_MIB}.2.2"
CISCO_IPSEC_SA_ENTRY = f"{CISCO_IPSEC_SA_TABLE}.1"
CISCO_IPSEC_SA_INDEX = f"{CISCO_IPSEC_SA_ENTRY}.1"
CISCO_IPSEC_SA_STATUS = f"{CISCO_IPSEC_SA_ENTRY}.5"  # cipsecSaStatus
CISCO_IPSEC_SA_ENCRYPT_ALG = f"{CISCO_IPSEC_SA_ENTRY}.8"  # cipsecSaEncryAlgorithm
CISCO_IPSEC_SA_BYTES_ENCRYPTED = f"{CISCO_IPSEC_SA_ENTRY}.15"  # cipsecSaInOctetsTotal
CISCO_IPSEC_SA_BYTES_DECRYPTED = f"{CISCO_IPSEC_SA_ENTRY}.20"  # cipsecSaOutOctetsTotal
CISCO_IPSEC_SA_DROP_PKTS = f"{CISCO_IPSEC_SA_ENTRY}.18"  # cipsecSaInDropPkts

# GRE MIB (RFC 2890 - GRE-MIB)
GRE_MIB = "1.3.6.1.2.1.10.126"
GRE_TUNNEL_TABLE = f"{GRE_MIB}.1"
GRE_TUNNEL_ENTRY = f"{GRE_TUNNEL_TABLE}.1"
GRE_TUNNEL_IF_INDEX = f"{GRE_TUNNEL_ENTRY}.1"
GRE_TUNNEL_SOURCE = f"{GRE_TUNNEL_ENTRY}.2"  # greTunnelSource
GRE_TUNNEL_DESTINATION = f"{GRE_TUNNEL_ENTRY}.3"  # greTunnelDestination
GRE_TUNNEL_STATUS = f"{GRE_TUNNEL_ENTRY}.4"  # greTunnelStatus

# DMVPN MIB (CISCO-DMVPN-MIB)
CISCO_DMVPN_MIB = "1.3.6.1.4.1.9.9.393"

# NHRP Cache Table
NHRP_CACHE_TABLE = f"{CISCO_DMVPN_MIB}.1.2"
NHRP_CACHE_ENTRY = f"{NHRP_CACHE_TABLE}.1"
NHRP_CACHE_PROTOCOL_ADDR = f"{NHRP_CACHE_ENTRY}.2"  # cdNhrpCacheProtocolAddr
NHRP_CACHE_NBMA_ADDR = f"{NHRP_CACHE_ENTRY}.3"  # cdNhrpCacheNbmaAddr
NHRP_CACHE_TYPE = f"{NHRP_CACHE_ENTRY}.4"  # cdNhrpCacheType (1=dynamic, 2=static)
NHRP_CACHE_REMAIN_TIME = f"{NHRP_CACHE_ENTRY}.6"  # cdNhrpCacheRemainTime

# DMVPN Tunnel Table
CISCO_DMVPN_TUNNEL_TABLE = f"{CISCO_DMVPN_MIB}.1.3"
CISCO_DMVPN_TUNNEL_ENTRY = f"{CISCO_DMVPN_TUNNEL_TABLE}.1"
CISCO_DMVPN_TUNNEL_IF_INDEX = f"{CISCO_DMVPN_TUNNEL_ENTRY}.1"
CISCO_DMVPN_TUNNEL_TYPE = f"{CISCO_DMVPN_TUNNEL_ENTRY}.2"  # cdTunnelType (1=hub, 2=spoke)

# ============================================
# Vendor-specific OIDs
# ============================================

# Juniper OIDs
JUNIPER_MIB = "1.3.6.1.4.1.2636"
JUNIPER_CPU = "1.3.6.1.4.1.2636.3.1.13.1.0"  # jnxOperatingCPU
JUNIPER_MEMORY = "1.3.6.1.4.1.2636.3.1.2.1.0"  # jnxOperatingBuffer

# HP/Aruba OIDs
HP_MIB = "1.3.6.1.4.1.11"
HP_CPU = "1.3.6.1.4.1.11.2.14.11.5.1.9.6.1.0"  # hpicfCpu
HP_MEMORY = "1.3.6.1.4.1.11.2.14.11.5.1.9.1.9.0"  # hpicfMem

# Fortinet OIDs
FORTINET_MIB = "1.3.6.1.4.1.12356"
FORTINET_CPU = "1.3.6.1.4.1.12356.101.4.1.1.0"  # fnSysCpuUsage
FORTINET_MEMORY = "1.3.6.1.4.1.12356.101.4.1.2.0"  # fnSysMemUsage

# ============================================
# State mappings
# ============================================

# Interface Admin/Oper Status
IF_STATUS_UP = 1
IF_STATUS_DOWN = 2
IF_STATUS_TESTING = 3

# OSPF Neighbor State (RFC 1850)
OSPF_STATE_DOWN = 1
OSPF_STATE_ATTEMPT = 2
OSPF_STATE_INIT = 3
OSPF_STATE_TWO_WAY = 4
OSPF_STATE_EX_START = 5
OSPF_STATE_EXCHANGE = 6
OSPF_STATE_LOADING = 7
OSPF_STATE_FULL = 8

# BGP Peer State (RFC 1657)
BGP_STATE_IDLE = 1
BGP_STATE_CONNECT = 2
BGP_STATE_ACTIVE = 3
BGP_STATE_OPEN_SENT = 4
BGP_STATE_OPEN_CONFIRM = 5
BGP_STATE_ESTABLISHED = 6

# IPSec Status
IPSEC_STATUS_ACTIVE = 1
IPSEC_STATUS_INACTIVE = 2
IPSEC_STATUS_NEGOTIATING = 3
IPSEC_STATUS_FAILED = 4


def get_ospf_state_name(state: int) -> str:
    """Convert OSPF state integer to name."""
    states = {
        OSPF_STATE_DOWN: "down",
        OSPF_STATE_ATTEMPT: "attempt",
        OSPF_STATE_INIT: "init",
        OSPF_STATE_TWO_WAY: "two_way",
        OSPF_STATE_EX_START: "ex_start",
        OSPF_STATE_EXCHANGE: "exchange",
        OSPF_STATE_LOADING: "loading",
        OSPF_STATE_FULL: "full",
    }
    return states.get(state, "unknown")


def get_bgp_state_name(state: int) -> str:
    """Convert BGP state integer to name."""
    states = {
        BGP_STATE_IDLE: "idle",
        BGP_STATE_CONNECT: "connect",
        BGP_STATE_ACTIVE: "active",
        BGP_STATE_OPEN_SENT: "open_sent",
        BGP_STATE_OPEN_CONFIRM: "open_confirm",
        BGP_STATE_ESTABLISHED: "established",
    }
    return states.get(state, "unknown")


def get_if_status_name(state: int) -> str:
    """Convert interface status integer to name."""
    statuses = {
        IF_STATUS_UP: "up",
        IF_STATUS_DOWN: "down",
        IF_STATUS_TESTING: "testing",
    }
    return statuses.get(state, "unknown")
