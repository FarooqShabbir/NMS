"""Alert service - alert processing and notifications."""
import json
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import httpx

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.device import Device
from ..models.alert import Alert, AlertRule, AlertStatus, AlertSeverity, AlertType, MaintenanceWindow
from ..core.config import settings


class AlertService:
    """Service for alert processing and notifications."""

    def __init__(self, db: Session):
        self.db = db

    # ============================================
    # Alert Creation
    # ============================================

    def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        device: Optional[Device] = None,
        interface_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        threshold_value: Optional[float] = None,
        current_value: Optional[float] = None,
    ) -> Optional[Alert]:
        """
        Create a new alert if not suppressed.

        Returns Alert or None if suppressed.
        """
        # Check for maintenance window
        if self._is_suppressed(device.id if device else None, alert_type):
            return None

        # Check for existing active alert of same type
        existing = (
            self.db.query(Alert)
            .filter(
                Alert.device_id == (device.id if device else None),
                Alert.alert_type == alert_type,
                Alert.status == AlertStatus.ACTIVE,
            )
            .first()
        )

        if existing:
            # Update existing alert
            existing.notification_count += 1
            existing.current_value = current_value
            existing.last_notified_at = datetime.utcnow()
            self.db.commit()
            return existing

        # Create new alert
        alert = Alert(
            device_id=device.id if device else None,
            interface_id=interface_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            details=json.dumps(details) if details else None,
            threshold_value=threshold_value,
            current_value=current_value,
        )

        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)

        return alert

    def _is_suppressed(
        self,
        device_id: Optional[int],
        alert_type: AlertType,
    ) -> bool:
        """Check if alert is suppressed by maintenance window."""
        now = datetime.utcnow()

        windows = (
            self.db.query(MaintenanceWindow)
            .filter(
                MaintenanceWindow.start_time <= now,
                MaintenanceWindow.end_time >= now,
            )
            .all()
        )

        for window in windows:
            # Check device scope
            if window.device_ids:
                device_ids = json.loads(window.device_ids)
                if device_id and device_id not in device_ids:
                    continue

            # Check alert type scope
            if window.alert_types:
                alert_types = json.loads(window.alert_types)
                if alert_type.value not in alert_types:
                    continue

            # Alert is suppressed
            return True

        return False

    # ============================================
    # Alert State Changes
    # ============================================

    def acknowledge_alert(
        self,
        alert_id: int,
        acknowledged_by: str,
        note: Optional[str] = None,
    ) -> Optional[Alert]:
        """Acknowledge an alert."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()
        alert.acknowledged_by = acknowledged_by
        alert.acknowledgment_note = note

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_alert(
        self,
        alert_id: int,
        resolution_note: Optional[str] = None,
    ) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self.db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        if resolution_note:
            alert.acknowledgment_note = resolution_note

        self.db.commit()
        self.db.refresh(alert)
        return alert

    def resolve_device_alerts(
        self,
        device_id: int,
        alert_type: Optional[AlertType] = None,
    ) -> int:
        """Resolve all active alerts for a device."""
        query = (
            self.db.query(Alert)
            .filter(
                Alert.device_id == device_id,
                Alert.status == AlertStatus.ACTIVE,
            )
        )

        if alert_type:
            query = query.filter(Alert.alert_type == alert_type)

        alerts = query.all()
        for alert in alerts:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()

        self.db.commit()
        return len(alerts)

    # ============================================
    # Alert Rules
    # ============================================

    def check_alert_rules(
        self,
        device: Device,
        metric: str,
        value: float,
    ) -> List[Alert]:
        """
        Check alert rules for a metric value.

        Returns list of created alerts.
        """
        created_alerts = []

        rules = (
            self.db.query(AlertRule)
            .filter(
                AlertRule.enabled == True,
                AlertRule.metric == metric,
            )
            .all()
        )

        for rule in rules:
            # Check device scope
            if rule.device_ids:
                device_ids = json.loads(rule.device_ids)
                if device.id not in device_ids:
                    continue

            # Evaluate condition
            triggered = self._evaluate_rule(rule, value)

            if triggered:
                alert = self.create_alert(
                    alert_type=rule.alert_type,
                    severity=rule.severity,
                    title=f"{rule.name} - {device.name}",
                    message=f"{metric} is {value} (threshold: {rule.operator} {rule.threshold_value})",
                    device=device,
                    threshold_value=rule.threshold_value,
                    current_value=value,
                )
                if alert:
                    created_alerts.append(alert)

        return created_alerts

    def _evaluate_rule(self, rule: AlertRule, value: float) -> bool:
        """Evaluate if a rule condition is met."""
        if rule.operator is None or rule.threshold_value is None:
            return False

        operators = {
            "gt": lambda v, t: v > t,
            "gte": lambda v, t: v >= t,
            "lt": lambda v, t: v < t,
            "lte": lambda v, t: v <= t,
            "eq": lambda v, t: v == t,
            "ne": lambda v, t: v != t,
        }

        op_func = operators.get(rule.operator)
        if not op_func:
            return False

        return op_func(value, rule.threshold_value)

    # ============================================
    # Notifications
    # ============================================

    async def send_notification(self, alert: Alert) -> Dict[str, bool]:
        """
        Send notifications for an alert.

        Returns dict of channel -> success status.
        """
        results = {}

        # Get alert rule for notification settings
        rule = (
            self.db.query(AlertRule)
            .filter(AlertRule.alert_type == alert.alert_type)
            .first()
        )

        if rule:
            # Email notification
            if rule.notify_email and settings.ALERT_EMAIL_ENABLED:
                results["email"] = await self._send_email_notification(alert)

            # Slack notification
            if rule.notify_slack and settings.ALERT_SLACK_ENABLED:
                results["slack"] = await self._send_slack_notification(alert)

            # Telegram notification
            if rule.notify_telegram and settings.ALERT_TELEGRAM_ENABLED:
                results["telegram"] = await self._send_telegram_notification(alert)

            # Webhook notification
            if rule.notify_webhook and rule.webhook_url:
                results["webhook"] = await self._send_webhook_notification(alert, rule.webhook_url)

        # Update notification tracking
        alert.notifications_sent = json.dumps(results)
        alert.last_notified_at = datetime.utcnow()
        alert.notification_count += 1

        self.db.commit()

        return results

    async def _send_email_notification(self, alert: Alert) -> bool:
        """Send email notification."""
        if not all([
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.SMTP_FROM_EMAIL,
        ]):
            return False

        # Implementation would use aiosmtplib or similar
        # For now, just log
        print(f"Email notification for alert {alert.id}: {alert.title}")
        return True

    async def _send_slack_notification(self, alert: Alert) -> bool:
        """Send Slack webhook notification."""
        if not settings.SLACK_WEBHOOK_URL:
            return False

        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ffcc00",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.EMERGENCY: "#800000",
        }

        payload = {
            "attachments": [
                {
                    "color": color_map.get(alert.severity, "#808080"),
                    "title": alert.title,
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value, "short": True},
                        {"title": "Device", "value": alert.device.name if alert.device else "N/A", "short": True},
                        {"title": "Type", "value": alert.alert_type.value, "short": True},
                        {"title": "Time", "value": alert.triggered_at.isoformat(), "short": True},
                    ],
                }
            ]
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.SLACK_WEBHOOK_URL,
                    json=payload,
                    timeout=10.0,
                )
                return response.status_code == 200
        except Exception:
            return False

    async def _send_telegram_notification(self, alert: Alert) -> bool:
        """Send Telegram notification."""
        if not all([settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_CHAT_ID]):
            return False

        emoji_map = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
            AlertSeverity.EMERGENCY: "🆘",
        }

        message = (
            f"{emoji_map.get(alert.severity, '❗')} *{alert.title}*\n\n"
            f"{alert.message}\n\n"
            f"*Device:* {alert.device.name if alert.device else 'N/A'}\n"
            f"*Severity:* {alert.severity.value}\n"
            f"*Type:* {alert.alert_type.value}"
        )

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                return response.status_code == 200
        except Exception:
            return False

    async def _send_webhook_notification(self, alert: Alert, webhook_url: str) -> bool:
        """Send webhook notification."""
        payload = {
            "alert_id": alert.id,
            "alert_type": alert.alert_type.value,
            "severity": alert.severity.value,
            "title": alert.title,
            "message": alert.message,
            "device_id": alert.device_id,
            "device_name": alert.device.name if alert.device else None,
            "triggered_at": alert.triggered_at.isoformat(),
            "threshold_value": alert.threshold_value,
            "current_value": alert.current_value,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=10.0)
                return response.status_code in (200, 201, 202)
        except Exception:
            return False

    # ============================================
    # Alert Processing (called by Celery)
    # ============================================

    def process_alerts(self) -> Dict[str, int]:
        """
        Process pending alerts and send notifications.

        Returns counts of processed alerts.
        """
        # Get active alerts that need notification
        alerts = (
            self.db.query(Alert)
            .filter(
                Alert.status == AlertStatus.ACTIVE,
                Alert.suppressed == False,
            )
            .all()
        )

        processed = 0
        failed = 0

        for alert in alerts:
            try:
                # Run async notification sending
                asyncio.run(self.send_notification(alert))
                processed += 1
            except Exception:
                failed += 1

        return {"processed": processed, "failed": failed}

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get alert summary statistics."""
        total = self.db.query(Alert).count()
        active = self.db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).count()
        acknowledged = self.db.query(Alert).filter(Alert.status == AlertStatus.ACKNOWLEDGED).count()
        resolved = self.db.query(Alert).filter(Alert.status == AlertStatus.RESOLVED).count()

        critical = (
            self.db.query(Alert)
            .filter(
                Alert.severity == AlertSeverity.CRITICAL,
                Alert.status == AlertStatus.ACTIVE,
            )
            .count()
        )
        warning = (
            self.db.query(Alert)
            .filter(
                Alert.severity == AlertSeverity.WARNING,
                Alert.status == AlertStatus.ACTIVE,
            )
            .count()
        )

        # Alerts by type
        by_type = (
            self.db.query(Alert.alert_type, func.count(Alert.id))
            .filter(Alert.status == AlertStatus.ACTIVE)
            .group_by(Alert.alert_type)
            .all()
        )

        return {
            "total_alerts": total,
            "active_alerts": active,
            "acknowledged_alerts": acknowledged,
            "resolved_alerts": resolved,
            "critical_alerts": critical,
            "warning_alerts": warning,
            "alerts_by_type": {t.value: c for t, c in by_type},
        }


from sqlalchemy.sql import func

# Factory function
def get_alert_service(db: Session) -> AlertService:
    """Get alert service instance."""
    return AlertService(db)
