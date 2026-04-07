"""VPN API router - IPSec, GRE, DMVPN."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.device import Device
from ..models.vpn import VPNTunnel, NHRPCache, IPSecSA, TunnelStatus
from ..schemas.vpn import (
    VPNTunnelResponse,
    NHRPCacheResponse,
    IPSecSAResponse,
    VPNSummaryResponse,
    DMVPNHubSummary,
)

router = APIRouter(prefix="/api/vpn", tags=["vpn"])


# ============================================
# VPN Tunnel Endpoints
# ============================================

@router.get("/tunnels", response_model=List[VPNTunnelResponse])
def list_vpn_tunnels(
    device_id: Optional[int] = Query(None),
    tunnel_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List VPN tunnels with optional filters."""
    query = db.query(VPNTunnel)

    if device_id:
        query = query.filter(VPNTunnel.device_id == device_id)
    if tunnel_type:
        query = query.filter(VPNTunnel.tunnel_type == tunnel_type)
    if status:
        query = query.filter(VPNTunnel.status == status)

    return query.all()


@router.get("/tunnels/{tunnel_id}", response_model=VPNTunnelResponse)
def get_vpn_tunnel(tunnel_id: int, db: Session = Depends(get_db)):
    """Get details of a specific VPN tunnel."""
    tunnel = db.query(VPNTunnel).filter(VPNTunnel.id == tunnel_id).first()
    if not tunnel:
        raise HTTPException(status_code=404, detail="VPN tunnel not found")
    return tunnel


@router.get("/summary")
def get_vpn_summary(db: Session = Depends(get_db)):
    """Get VPN summary statistics."""
    total = db.query(VPNTunnel).count()
    up = db.query(VPNTunnel).filter(VPNTunnel.status == TunnelStatus.UP).count()
    down = db.query(VPNTunnel).filter(VPNTunnel.status == TunnelStatus.DOWN).count()

    # Count by type
    ipsec_count = db.query(VPNTunnel).filter(VPNTunnel.tunnel_type == "ipsec").count()
    gre_count = db.query(VPNTunnel).filter(VPNTunnel.tunnel_type == "gre").count()
    dmvpn_count = db.query(VPNTunnel).filter(VPNTunnel.tunnel_type == "dmvpn").count()

    # Active IPSec SAs
    ipsec_sas = db.query(IPSecSA).filter(IPSecSA.status == "active").count()

    return {
        "total_tunnels": total,
        "tunnels_up": up,
        "tunnels_down": down,
        "ipsec_tunnels": ipsec_count,
        "gre_tunnels": gre_count,
        "dmvpn_tunnels": dmvpn_count,
        "ipsec_sas_active": ipsec_sas,
    }


@router.get("/summary/{device_id}", response_model=VPNSummaryResponse)
def get_device_vpn_summary(device_id: int, db: Session = Depends(get_db)):
    """Get VPN summary for a specific device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    tunnels = db.query(VPNTunnel).filter(VPNTunnel.device_id == device_id).all()
    total = len(tunnels)
    up = sum(1 for t in tunnels if t.status == TunnelStatus.UP)
    down = sum(1 for t in tunnels if t.status == TunnelStatus.DOWN)

    # DMVPN spokes
    dmvpn_spokes = sum(
        1 for t in tunnels
        if t.tunnel_type == "dmvpn" and t.nhrp_peer_type == "spoke"
    )

    # IPSec SAs
    ipsec_sas = db.query(IPSecSA).filter(IPSecSA.device_id == device_id, IPSecSA.status == "active").count()

    return VPNSummaryResponse(
        device_id=device_id,
        total_tunnels=total,
        tunnels_up=up,
        tunnels_down=down,
        dmvpn_spokes=dmvpn_spokes,
        ipsec_sas_active=ipsec_sas,
    )


# ============================================
# DMVPN / NHRP Endpoints
# ============================================

@router.get("/dmvpn/nhrp-cache", response_model=List[NHRPCacheResponse])
def list_nhrp_cache(
    device_id: Optional[int] = Query(None),
    entry_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List NHRP cache entries."""
    query = db.query(NHRPCache)

    if device_id:
        query = query.filter(NHRPCache.device_id == device_id)
    if entry_type:
        query = query.filter(NHRPCache.entry_type == entry_type)

    return query.all()


@router.get("/dmvpn/hubs")
def list_dmvpn_hubs(db: Session = Depends(get_db)):
    """List DMVPN hub devices with spoke information."""
    # Find tunnels configured as hubs
    hub_tunnels = (
        db.query(VPNTunnel)
        .filter(
            VPNTunnel.tunnel_type == "dmvpn",
            VPNTunnel.nhrp_peer_type == "hub",
        )
        .all()
    )

    results = []
    for tunnel in hub_tunnels:
        device = db.query(Device).filter(Device.id == tunnel.device_id).first()

        # Count spokes in NHRP cache
        spokes = (
            db.query(NHRPCache)
            .filter(NHRPCache.device_id == tunnel.device_id)
            .all()
        )

        connected = sum(1 for s in spokes if s.remaining_time > 0)
        disconnected = sum(1 for s in spokes if s.remaining_time <= 0)

        results.append(
            DMVPNHubSummary(
                hub_device_id=tunnel.device_id,
                hub_name=device.name if device else "Unknown",
                total_spokes=len(spokes),
                spokes_connected=connected,
                spokes_disconnected=disconnected,
                tunnel_interface=tunnel.tunnel_interface or "N/A",
                nhrp_cache_entries=len(spokes),
            ).dict()
        )

    return results


@router.get("/dmvpn/spokes")
def list_dmvpn_spokes(db: Session = Depends(get_db)):
    """List DMVPN spoke devices."""
    spoke_tunnels = (
        db.query(VPNTunnel)
        .filter(
            VPNTunnel.tunnel_type == "dmvpn",
            VPNTunnel.nhrp_peer_type == "spoke",
        )
        .all()
    )

    results = []
    for tunnel in spoke_tunnels:
        device = db.query(Device).filter(Device.id == tunnel.device_id).first()
        results.append({
            "device_id": tunnel.device_id,
            "device_name": device.name if device else "Unknown",
            "tunnel_name": tunnel.tunnel_name,
            "tunnel_interface": tunnel.tunnel_interface,
            "status": tunnel.status.value,
            "hub_reachable": tunnel.status == TunnelStatus.UP,
        })

    return results


# ============================================
# IPSec SA Endpoints
# ============================================

@router.get("/ipsec/sas", response_model=List[IPSecSAResponse])
def list_ipsec_sas(
    device_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List IPSec Security Associations."""
    query = db.query(IPSecSA)

    if device_id:
        query = query.filter(IPSecSA.device_id == device_id)
    if status:
        query = query.filter(IPSecSA.status == status)

    return query.all()


@router.get("/ipsec/sas/{sa_id}", response_model=IPSecSAResponse)
def get_ipsec_sa(sa_id: int, db: Session = Depends(get_db)):
    """Get details of a specific IPSec SA."""
    sa = db.query(IPSecSA).filter(IPSecSA.id == sa_id).first()
    if not sa:
        raise HTTPException(status_code=404, detail="IPSec SA not found")
    return sa
