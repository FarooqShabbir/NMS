"""Celery configuration and app instance."""
from celery import Celery
from celery.schedules import crontab

from .config import settings


def make_celery() -> Celery:
    """Create and configure the Celery application."""
    celery_app = Celery(
        'nms',
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            'app.tasks.polling_tasks',
            'app.tasks.backup_tasks',
            'app.tasks.alert_tasks',
        ]
    )

    # Celery configuration
    celery_app.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes max per task
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )

    # Scheduled tasks
    celery_app.conf.beat_schedule = {
        # Health polling every minute
        'poll-device-health-every-minute': {
            'task': 'app.tasks.polling_tasks.poll_device_health',
            'schedule': 60.0,
        },
        # Interface stats every minute
        'poll-interface-stats-every-minute': {
            'task': 'app.tasks.polling_tasks.poll_interface_stats',
            'schedule': 60.0,
        },
        # Routing protocols every 5 minutes
        'poll-routing-protocols-every-5-minutes': {
            'task': 'app.tasks.polling_tasks.poll_routing_protocols',
            'schedule': 300.0,
        },
        # VPN status every 5 minutes
        'poll-vpn-status-every-5-minutes': {
            'task': 'app.tasks.polling_tasks.poll_vpn_status',
            'schedule': 300.0,
        },
        # Daily backup at 2 AM
        'daily-backup-at-2am': {
            'task': 'app.tasks.backup_tasks.run_scheduled_backups',
            'schedule': crontab(hour=2, minute=0),
        },
        # Check alerts every 30 seconds
        'check-alerts-every-30-seconds': {
            'task': 'app.tasks.alert_tasks.process_alerts',
            'schedule': 30.0,
        },
        # Cleanup old backups weekly
        'cleanup-old-backups-weekly': {
            'task': 'app.tasks.backup_tasks.cleanup_old_backups',
            'schedule': crontab(hour=3, minute=0, day_of_week=0),
        },
    }

    return celery_app


celery_app = make_celery()
