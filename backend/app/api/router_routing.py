"""Routing protocol API router - BGP, OSPF, EIGRP."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.device import Device
from ..models.routing import BGPNeighbor, OSPFNeighbor, EIGRPNeighbor, OSPFProcess, EIGRPProcess
from ..schemas.routing import (
    BGPNeighborResponse,
    OSPFNeighborResponse,
    OSPFProcessResponse,
    EIGRPNeighborResponse,
    EIGRPProcessResponse,
    RoutingSummaryResponse,
)

router = APIRouter(prefix="/api/routing", tags=["routing"])


# ============================================
# BGP Endpoints
# ============================================

@router.get("/bgp/neighbors", response_model=List[BGPNeighborResponse])
def list_bgp_neighbors(
    device_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List BGP neighbors with optional filters."""
    query = db.query(BGPNeighbor)

    if device_id:
        query = query.filter(BGPNeighbor.device_id == device_id)
    if state:
        query = query.filter(BGPNeighbor.state == state)

    return query.all()


@router.get("/bgp/neighbors/{neighbor_id}", response_model=BGPNeighborResponse)
def get_bgp_neighbor(neighbor_id: int, db: Session = Depends(get_db)):
    """Get details of a specific BGP neighbor."""
    neighbor = db.query(BGPNeighbor).filter(BGPNeighbor.id == neighbor_id).first()
    if not neighbor:
        raise HTTPException(status_code=404, detail="BGP neighbor not found")
    return neighbor


@router.get("/bgp/summary")
def get_bgp_summary(db: Session = Depends(get_db)):
    """Get BGP summary statistics."""
    total = db.query(BGPNeighbor).count()
    established = db.query(BGPNeighbor).filter(BGPNeighbor.state == "established").count()
    idle = db.query(BGPNeighbor).filter(BGPNeighbor.state == "idle").count()
    active = db.query(BGPNeighbor).filter(BGPNeighbor.state == "active").count()

    # Get devices with BGP
    devices_with_bgp = (
        db.query(BGPNeighbor.device_id)
        .distinct()
        .all()
    )

    return {
        "total_neighbors": total,
        "established": established,
        "idle": idle,
        "active": active,
        "devices_with_bgp": len(devices_with_bgp),
    }


# ============================================
# OSPF Endpoints
# ============================================

@router.get("/ospf/neighbors", response_model=List[OSPFNeighborResponse])
def list_ospf_neighbors(
    device_id: Optional[int] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List OSPF neighbors with optional filters."""
    query = db.query(OSPFNeighbor)

    if device_id:
        query = query.filter(OSPFNeighbor.device_id == device_id)
    if state:
        query = query.filter(OSPFNeighbor.state == state)

    return query.all()


@router.get("/ospf/neighbors/{neighbor_id}", response_model=OSPFNeighborResponse)
def get_ospf_neighbor(neighbor_id: int, db: Session = Depends(get_db)):
    """Get details of a specific OSPF neighbor."""
    neighbor = db.query(OSPFNeighbor).filter(OSPFNeighbor.id == neighbor_id).first()
    if not neighbor:
        raise HTTPException(status_code=404, detail="OSPF neighbor not found")
    return neighbor


@router.get("/ospf/processes", response_model=List[OSPFProcessResponse])
def list_ospf_processes(db: Session = Depends(get_db)):
    """List OSPF processes."""
    return db.query(OSPFProcess).all()


@router.get("/ospf/summary")
def get_ospf_summary(db: Session = Depends(get_db)):
    """Get OSPF summary statistics."""
    total = db.query(OSPFNeighbor).count()
    full = db.query(OSPFNeighbor).filter(OSPFNeighbor.state == "full").count()
    down = db.query(OSPFNeighbor).filter(OSPFNeighbor.state == "down").count()
    two_way = db.query(OSPFNeighbor).filter(OSPFNeighbor.state == "two_way").count()

    # Get devices with OSPF
    devices_with_ospf = (
        db.query(OSPFNeighbor.device_id)
        .distinct()
        .all()
    )

    return {
        "total_neighbors": total,
        "full_adjacencies": full,
        "down": down,
        "two_way": two_way,
        "devices_with_ospf": len(devices_with_ospf),
    }


# ============================================
# EIGRP Endpoints
# ============================================

@router.get("/eigrp/neighbors", response_model=List[EIGRPNeighborResponse])
def list_eigrp_neighbors(
    device_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """List EIGRP neighbors with optional filters."""
    query = db.query(EIGRPNeighbor)

    if device_id:
        query = query.filter(EIGRPNeighbor.device_id == device_id)

    return query.all()


@router.get("/eigrp/neighbors/{neighbor_id}", response_model=EIGRPNeighborResponse)
def get_eigrp_neighbor(neighbor_id: int, db: Session = Depends(get_db)):
    """Get details of a specific EIGRP neighbor."""
    neighbor = db.query(EIGRPNeighbor).filter(EIGRPNeighbor.id == neighbor_id).first()
    if not neighbor:
        raise HTTPException(status_code=404, detail="EIGRP neighbor not found")
    return neighbor


@router.get("/eigrp/processes", response_model=List[EIGRPProcessResponse])
def list_eigrp_processes(db: Session = Depends(get_db)):
    """List EIGRP processes."""
    return db.query(EIGRPProcess).all()


@router.get("/eigrp/summary")
def get_eigrp_summary(db: Session = Depends(get_db)):
    """Get EIGRP summary statistics."""
    total = db.query(EIGRPNeighbor).count()

    # Get devices with EIGRP
    devices_with_eigrp = (
        db.query(EIGRPNeighbor.device_id)
        .distinct()
        .all()
    )

    return {
        "total_neighbors": total,
        "devices_with_eigrp": len(devices_with_eigrp),
    }


# ============================================
# Combined Routing Summary
# ============================================

@router.get("/summary/{device_id}", response_model=RoutingSummaryResponse)
def get_routing_summary(device_id: int, db: Session = Depends(get_db)):
    """Get routing protocol summary for a specific device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    bgp_count = db.query(BGPNeighbor).filter(BGPNeighbor.device_id == device_id).count()
    bgp_established = (
        db.query(BGPNeighbor)
        .filter(BGPNeighbor.device_id == device_id, BGPNeighbor.state == "established")
        .count()
    )

    ospf_count = db.query(OSPFNeighbor).filter(OSPFNeighbor.device_id == device_id).count()
    ospf_full = (
        db.query(OSPFNeighbor)
        .filter(OSPFNeighbor.device_id == device_id, OSPFNeighbor.state == "full")
        .count()
    )

    eigrp_count = db.query(EIGRPNeighbor).filter(EIGRPNeighbor.device_id == device_id).count()

    return RoutingSummaryResponse(
        device_id=device_id,
        bgp_neighbors_count=bgp_count,
        bgp_established_count=bgp_established,
        ospf_neighbors_count=ospf_count,
        ospf_full_count=ospf_full,
        eigrp_neighbors_count=eigrp_count,
        eigrp_established_count=eigrp_count,
    )
