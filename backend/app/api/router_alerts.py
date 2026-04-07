"""Alert management API router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import get_db
from ..models.device import Device
from ..models.alert import Alert, AlertRule, MaintenanceWindow, AlertStatus, AlertSeverity, AlertType
from ..schemas.alert import (
    AlertResponse,
    AlertUpdate,
    AlertAcknowledgeRequest,
    AlertRuleResponse,
    AlertRuleCreate,
    AlertRuleUpdate,
    MaintenanceWindowResponse,
    MaintenanceWindowCreate,
    AlertSummaryResponse,
    AlertTimelineResponse,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# ============================================
# Alert Endpoints
# ============================================

@router.get("", response_model=List[AlertResponse])
def list_alerts(
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    alert_type: Optional[str] = Query(None),
    device_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List alerts with optional filters."""
    query = db.query(Alert)

    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if device_id:
        query = query.filter(Alert.device_id == device_id)

    query = query.order_by(Alert.triggered_at.desc())

    alerts = query.offset(skip).limit(limit).all()

    # Enrich with device info
    results = []
    for alert in alerts:
        device = db.query(Device).filter(Device.id == alert.device_id).first() if alert.device_id else None
        results.append(
            AlertResponse(
                id=alert.id,
                device_id=alert.device_id,
                device_name=device.name if device else None,
                alert_type=alert.alert_type,
                severity=alert.severity,
                status=alert.status,
                title=alert.title,
                message=alert.message,
                triggered_at=alert.triggered_at,
                acknowledged_at=alert.acknowledged_at,
                resolved_at=alert.resolved_at,
                acknowledged_by=alert.acknowledged_by,
                notification_count=alert.notification_count,
            )
        )

    return results


@router.get("/summary", response_model=AlertSummaryResponse)
def get_alert_summary(db: Session = Depends(get_db)):
    """Get alert summary statistics."""
    total = db.query(Alert).count()
    active = db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
    acknowledged = db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
    resolved = db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()

    critical = (
        db.query(Alert)
        .filter(Alert.severity == AlertSeverity.CRITICAL, Alert.status == AlertStatus.ACTIVE)
        .count()
    )
    warning = (
        db.query(Alert)
        .filter(Alert.severity == AlertSeverity.WARNING, Alert.status == AlertStatus.ACTIVE)
        .count()
    )

    # By type
    by_type_query = (
        db.query(Alert.alert_type, func.count(Alert.id))
        .filter(Alert.status == AlertStatus.ACTIVE)
        .group_by(Alert.alert_type)
        .all()
    )
    alerts_by_type = {t.value: c for t, c in by_type_query}

    # By severity
    by_severity_query = (
        db.query(Alert.severity, func.count(Alert.id))
        .filter(Alert.status == AlertStatus.ACTIVE)
        .group_by(Alert.severity)
        .all()
    )
    alerts_by_severity = {s.value: c for s, c in by_severity_query}

    return AlertSummaryResponse(
        total_alerts=total,
        active_alerts=active,
        acknowledged_alerts=acknowledged,
        resolved_alerts=resolved,
        critical_alerts=critical,
        warning_alerts=warning,
        alerts_by_type=alerts_by_type,
        alerts_by_severity=alerts_by_severity,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int, db: Session = Depends(get_db)):
    """Get details of a specific alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    device = db.query(Device).filter(Device.id == alert.device_id).first() if alert.device_id else None

    return AlertResponse(
        id=alert.id,
        device_id=alert.device_id,
        device_name=device.name if device else None,
        alert_type=alert.alert_type,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        message=alert.message,
        triggered_at=alert.triggered_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        acknowledged_by=alert.acknowledged_by,
        notification_count=alert.notification_count,
    )


@router.put("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
):
    """Acknowledge an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = func.now()
    alert.acknowledgment_note = request.acknowledgment_note

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"message": "Alert acknowledged", "alert_id": alert_id}


@router.put("/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    request: AlertAcknowledgeRequest = None,
    db: Session = Depends(get_db),
):
    """Resolve an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.status = AlertStatus.RESOLVED
    alert.resolved_at = func.now()
    if request and request.acknowledgment_note:
        alert.acknowledgment_note = request.acknowledgment_note

    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {"message": "Alert resolved", "alert_id": alert_id}



@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    """Delete an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    db.delete(alert)
    db.commit()

    return {"message": "Alert deleted"}


@router.get("/timeline", response_model=List[AlertTimelineResponse])
def get_alert_timeline(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    """Get alert timeline for the last N hours."""
    from datetime import datetime, timedelta

    cutoff = datetime.utcnow() - timedelta(hours=hours)

    alerts = (
        db.query(Alert)
        .filter(Alert.triggered_at >= cutoff)
        .order_by(Alert.triggered_at.desc())
        .limit(100)
        .all()
    )

    results = []
    for alert in alerts:
        device = db.query(Device).filter(Device.id == alert.device_id).first() if alert.device_id else None
        results.append(
            AlertTimelineResponse(
                timestamp=alert.triggered_at,
                alert_type=alert.alert_type,
                severity=alert.severity,
                title=alert.title,
                device_name=device.name if device else None,
                status=alert.status,
            )
        )

    return results


# ============================================
# Alert Rule Endpoints
# ============================================

@router.get("/rules", response_model=List[AlertRuleResponse])
def list_alert_rules(db: Session = Depends(get_db)):
    """List all alert rules."""
    return db.query(AlertRule).all()


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
def create_alert_rule(rule_data: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create a new alert rule."""
    rule = AlertRule(
        name=rule_data.name,
        description=rule_data.description,
        enabled=rule_data.enabled,
        alert_type=rule_data.alert_type,
        severity=rule_data.severity,
        metric=rule_data.metric,
        operator=rule_data.operator,
        threshold_value=rule_data.threshold_value,
        duration_seconds=rule_data.duration_seconds,
        notify_email=rule_data.notify_email,
        notify_slack=rule_data.notify_slack,
        notify_telegram=rule_data.notify_telegram,
        notify_webhook=rule_data.notify_webhook,
        webhook_url=rule_data.webhook_url,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    db: Session = Depends(get_db),
):
    """Update an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.add(rule)
    db.commit()
    db.refresh(rule)

    return rule


@router.delete("/rules/{rule_id}")
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete an alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()

    return {"message": "Rule deleted"}


# ============================================
# Maintenance Window Endpoints
# ============================================

@router.get("/maintenance", response_model=List[MaintenanceWindowResponse])
def list_maintenance_windows(db: Session = Depends(get_db)):
    """List all maintenance windows."""
    return db.query(MaintenanceWindow).all()


@router.post("/maintenance", response_model=MaintenanceWindowResponse, status_code=201)
def create_maintenance_window(
    window_data: MaintenanceWindowCreate,
    db: Session = Depends(get_db),
):
    """Create a new maintenance window."""
    window = MaintenanceWindow(
        name=window_data.name,
        description=window_data.description,
        start_time=window_data.start_time,
        end_time=window_data.end_time,
        recurring=window_data.recurring,
        suppress_notifications=window_data.suppress_notifications,
    )

    db.add(window)
    db.commit()
    db.refresh(window)

    return window


@router.delete("/maintenance/{window_id}")
def delete_maintenance_window(window_id: int, db: Session = Depends(get_db)):
    """Delete a maintenance window."""
    window = db.query(MaintenanceWindow).filter(MaintenanceWindow.id == window_id).first()
    if not window:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    db.delete(window)
    db.commit()

    return {"message": "Maintenance window deleted"}
