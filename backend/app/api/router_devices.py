"""Device management API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..core.database import get_db
from ..core.task_dispatcher import dispatch_task
from ..models.device import Device, DeviceGroup, Interface, DeviceHealth, DeviceStatus
from ..schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceDetailResponse,
    DeviceHealthResponse,
    InterfaceResponse,
    DeviceGroupCreate,
    DeviceGroupResponse,
)
from ..services.snmp_service import snmp_service
from ..services.device_health_service import DeviceHealthService
from ..tasks.polling_tasks import poll_single_device
from ..tasks.backup_tasks import backup_device

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("", response_model=List[DeviceResponse])
def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    device_type: Optional[str] = None,
    status: Optional[str] = None,
    group_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all devices with optional filters."""
    query = db.query(Device)

    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)
    if group_id:
        query = query.filter(Device.group_id == group_id)
    if search:
        query = query.filter(
            or_(
                Device.name.ilike(f"%{search}%"),
                Device.ip_address.ilike(f"%{search}%"),
                Device.description.ilike(f"%{search}%"),
            )
        )

    return query.offset(skip).limit(limit).all()


@router.get("/count")
def get_device_count(
    db: Session = Depends(get_db),
):
    """Get total device count and status breakdown."""
    total = db.query(Device).count()
    up = db.query(Device).filter(Device.status == DeviceStatus.UP).count()
    down = db.query(Device).filter(Device.status == DeviceStatus.DOWN).count()
    warning = db.query(Device).filter(Device.status == DeviceStatus.WARNING).count()
    unknown = db.query(Device).filter(Device.status == DeviceStatus.UNKNOWN).count()

    return {
        "total": total,
        "up": up,
        "down": down,
        "warning": warning,
        "unknown": unknown,
    }


@router.get("/{device_id}", response_model=DeviceDetailResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.post("", response_model=DeviceResponse, status_code=201)
def create_device(
    device_data: DeviceCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Create a new network device."""
    # Check for duplicate IP
    existing = db.query(Device).filter(Device.ip_address == str(device_data.ip_address)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Device with this IP already exists")

    # Create device
    device = Device(
        name=device_data.name,
        ip_address=str(device_data.ip_address),
        description=device_data.description,
        device_type=device_data.device_type,
        location=device_data.location,
        department=device_data.department,
        group_id=device_data.group_id,
        polling_enabled=device_data.polling_enabled,
        polling_interval=device_data.polling_interval,
        snmp_version=device_data.snmp_version,
        snmp_community=device_data.snmp_community,
        snmp_v3_username=device_data.snmp_v3_username,
        snmp_v3_auth_protocol=device_data.snmp_v3_auth_protocol,
        snmp_v3_auth_password=device_data.snmp_v3_auth_password,
        snmp_v3_priv_protocol=device_data.snmp_v3_priv_protocol,
        snmp_v3_priv_password=device_data.snmp_v3_priv_password,
        ssh_username=device_data.ssh_username,
        ssh_password=device_data.ssh_password,
        ssh_key=device_data.ssh_key,
        ssh_port=device_data.ssh_port,
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    # Trigger initial poll in background
    dispatch_task(background_tasks, poll_single_device, device.id)

    return device


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(
    device_id: int,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
):
    """Update a device configuration."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Update fields
    update_data = device_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "ip_address" and value:
            value = str(value)
        setattr(device, field, value)

    db.add(device)
    db.commit()
    db.refresh(device)

    # Re-poll device
    dispatch_task(background_tasks, poll_single_device, device.id)

    return device


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    """Delete a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()

    return {"message": f"Device {device.name} deleted"}


@router.post("/{device_id}/test-connection")
def test_device_connection(device_id: int, db: Session = Depends(get_db)):
    """Test SNMP connection to a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    success, message = snmp_service.test_connection(device)

    return {
        "success": success,
        "message": message,
    }


@router.post("/{device_id}/poll")
def poll_device_now(device_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Trigger immediate polling of a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Trigger polling tasks
    task_id = dispatch_task(background_tasks, poll_single_device, device.id)

    return {
        "message": f"Polling triggered for device {device.name}",
        "task_id": task_id,
    }


@router.post("/{device_id}/backup")
def backup_device_now(
    device_id: int,
    backup_type: str = Query("running_config", regex="^(running_config|startup_config|full)$"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """Trigger immediate backup of a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Trigger backup task
    task_id = dispatch_task(
        background_tasks,
        backup_device,
        device_id=device.id,
        backup_type=backup_type,
        backup_method="ssh",
        created_by="api",
    )

    return {
        "message": f"Backup triggered for device {device.name}",
        "task_id": task_id,
    }


@router.get("/{device_id}/health", response_model=DeviceHealthResponse)
def get_device_health(device_id: int, db: Session = Depends(get_db)):
    """Get current health metrics for a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    health = db.query(DeviceHealth).filter(DeviceHealth.device_id == device_id).first()
    if not health:
        raise HTTPException(status_code=404, detail="No health data available")

    return health


@router.get("/{device_id}/interfaces", response_model=List[InterfaceResponse])
def get_device_interfaces(device_id: int, db: Session = Depends(get_db)):
    """Get all interfaces for a device."""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    interfaces = db.query(Interface).filter(Interface.device_id == device_id).all()
    return interfaces


# Device Groups
@router.get("/groups", response_model=List[DeviceGroupResponse])
def list_device_groups(db: Session = Depends(get_db)):
    """List all device groups."""
    groups = db.query(DeviceGroup).all()
    result = []
    for group in groups:
        device_count = db.query(Device).filter(Device.group_id == group.id).count()
        result.append(DeviceGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            device_count=device_count,
        ))
    return result


@router.post("/groups", response_model=DeviceGroupResponse, status_code=201)
def create_device_group(group_data: DeviceGroupCreate, db: Session = Depends(get_db)):
    """Create a new device group."""
    existing = db.query(DeviceGroup).filter(DeviceGroup.name == group_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group with this name already exists")

    group = DeviceGroup(
        name=group_data.name,
        description=group_data.description,
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    return group


@router.delete("/groups/{group_id}")
def delete_device_group(group_id: int, db: Session = Depends(get_db)):
    """Delete a device group."""
    group = db.query(DeviceGroup).filter(DeviceGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Unassign devices from this group
    db.query(Device).filter(Device.group_id == group_id).update({"group_id": None})

    db.delete(group)
    db.commit()

    return {"message": f"Group {group.name} deleted"}
