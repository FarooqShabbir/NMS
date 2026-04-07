"""Celery tasks for alert processing."""
from celery import current_task
import logging

from ..core.celery_config import celery_app
from ..core.database import SessionLocal
from ..services.alert_service import AlertService

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def process_alerts(self):
    """
    Process pending alerts and send notifications.

    Called periodically by Celery Beat.
    """
    db = SessionLocal()
    try:
        alert_service = AlertService(db)
        result = alert_service.process_alerts()
        return result

    except Exception as e:
        logger.error(f"Error processing alerts: {e}")
        raise self.retry(exc=e, countdown=30)
    finally:
        db.close()


@celery_app.task
def send_alert_notification(alert_id: int):
    """
    Send notification for a specific alert.

    Args:
        alert_id: Alert ID to notify
    """
    db = SessionLocal()
    try:
        alert_service = AlertService(db)

        # Get alert
        from ..models.alert import Alert
        alert = db.query(Alert).filter(Alert.id == alert_id).first()

        if not alert:
            return {"error": f"Alert {alert_id} not found"}

        # Send notification
        import asyncio
        result = asyncio.run(alert_service.send_notification(alert))

        return {
            "alert_id": alert_id,
            "notification_results": result,
        }

    except Exception as e:
        logger.error(f"Error sending alert notification: {e}")
        return {"alert_id": alert_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task
def escalate_alert(alert_id: int):
    """
    Escalate an alert to higher severity.

    Called when alert remains unacknowledged for too long.
    """
    db = SessionLocal()
    try:
        from ..models.alert import Alert, AlertSeverity

        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return {"error": f"Alert {alert_id} not found"}

        # Escalate severity
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.CRITICAL,
            AlertSeverity.EMERGENCY,
        ]

        current_index = severity_order.index(alert.severity)
        if current_index < len(severity_order) - 1:
            alert.severity = severity_order[current_index + 1]
            db.commit()

            return {
                "alert_id": alert_id,
                "new_severity": alert.severity.value,
                "escalated": True,
            }
        else:
            return {
                "alert_id": alert_id,
                "message": "Already at maximum severity",
                "escalated": False,
            }

    except Exception as e:
        logger.error(f"Error escalating alert: {e}")
        db.rollback()
        return {"alert_id": alert_id, "error": str(e)}
    finally:
        db.close()


@celery_app.task
def auto_resolve_alerts(device_id: int, alert_type: str = None):
    """
    Auto-resolve alerts when device recovers.

    Called after device comes back up.
    """
    db = SessionLocal()
    try:
        alert_service = AlertService(db)

        from ..models.alert import AlertType, AlertStatus

        alert_type_enum = AlertType(alert_type) if alert_type else None

        resolved = alert_service.resolve_device_alerts(
            device_id=device_id,
            alert_type=alert_type_enum,
        )

        return {
            "device_id": device_id,
            "resolved_count": resolved,
        }

    except Exception as e:
        logger.error(f"Error auto-resolving alerts: {e}")
        db.rollback()
        return {"device_id": device_id, "error": str(e)}
    finally:
        db.close()
