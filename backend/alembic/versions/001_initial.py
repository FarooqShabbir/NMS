"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2026-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('totp_secret', sa.String(length=255), nullable=True),
        sa.Column('totp_enabled', sa.Boolean(), default=False),
        sa.Column('role', sa.Enum('ADMIN', 'OPERATOR', 'VIEWER', 'BACKUP_ADMIN', name='userrole'), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.String(length=512), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('success', sa.Boolean(), default=True),
        sa.Column('error_message', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)

    # Device groups table
    op.create_table('device_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_device_groups_id'), 'device_groups', ['id'], unique=False)

    # Devices table
    op.create_table('devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('device_type', sa.Enum('ROUTER', 'SWITCH', 'FIREWALL', 'SERVER', 'PRINTER', 'ACCESS_POINT', 'OTHER', name='devicetype'), nullable=True),
        sa.Column('status', sa.Enum('UP', 'DOWN', 'WARNING', 'UNKNOWN', name='devicestatus'), nullable=True),
        sa.Column('snmp_version', sa.Enum('V1', 'V2C', 'V3', name='snmpversion'), nullable=True),
        sa.Column('snmp_community', sa.String(length=255), nullable=True),
        sa.Column('snmp_v3_username', sa.String(length=255), nullable=True),
        sa.Column('snmp_v3_auth_protocol', sa.String(length=10), nullable=True),
        sa.Column('snmp_v3_auth_password', sa.String(length=255), nullable=True),
        sa.Column('snmp_v3_priv_protocol', sa.String(length=10), nullable=True),
        sa.Column('snmp_v3_priv_password', sa.String(length=255), nullable=True),
        sa.Column('ssh_username', sa.String(length=255), nullable=True),
        sa.Column('ssh_password', sa.String(length=255), nullable=True),
        sa.Column('ssh_key', sa.Text(), nullable=True),
        sa.Column('ssh_port', sa.Integer(), default=22),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('device_groups.id'), nullable=True),
        sa.Column('polling_enabled', sa.Boolean(), default=True),
        sa.Column('polling_interval', sa.Integer(), default=60),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_devices_id'), 'devices', ['id'], unique=False)
    op.create_index(op.f('ix_devices_ip_address'), 'devices', ['ip_address'], unique=True)
    op.create_index(op.f('ix_devices_name'), 'devices', ['name'], unique=False)

    # Interfaces table
    op.create_table('interfaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('if_index', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('subnet_mask', sa.String(length=15), nullable=True),
        sa.Column('mtu', sa.Integer(), nullable=True),
        sa.Column('speed', sa.BigInteger(), nullable=True),
        sa.Column('duplex', sa.String(length=10), nullable=True),
        sa.Column('admin_status', sa.String(length=20), default='unknown'),
        sa.Column('oper_status', sa.String(length=20), default='unknown'),
        sa.Column('if_type', sa.String(length=50), nullable=True),
        sa.Column('in_octets', sa.BigInteger(), default=0),
        sa.Column('out_octets', sa.BigInteger(), default=0),
        sa.Column('in_unicast_packets', sa.BigInteger(), default=0),
        sa.Column('out_unicast_packets', sa.BigInteger(), default=0),
        sa.Column('in_errors', sa.BigInteger(), default=0),
        sa.Column('out_errors', sa.BigInteger(), default=0),
        sa.Column('in_discards', sa.BigInteger(), default=0),
        sa.Column('out_discards', sa.BigInteger(), default=0),
        sa.Column('utilization_in', sa.Float(), default=0.0),
        sa.Column('utilization_out', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interfaces_id'), 'interfaces', ['id'], unique=False)

    # Device health table
    op.create_table('device_health',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False, unique=True),
        sa.Column('cpu_usage', sa.Float(), default=0.0),
        sa.Column('memory_usage', sa.Float(), default=0.0),
        sa.Column('memory_total', sa.BigInteger(), default=0),
        sa.Column('memory_used', sa.BigInteger(), default=0),
        sa.Column('disk_usage', sa.Float(), default=0.0),
        sa.Column('temperature', sa.Float(), nullable=True),
        sa.Column('fan_status', sa.String(length=50), nullable=True),
        sa.Column('power_status', sa.String(length=50), nullable=True),
        sa.Column('uptime', sa.BigInteger(), default=0),
        sa.Column('last_polled', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_device_health_id'), 'device_health', ['id'], unique=False)

    # BGP neighbors table
    op.create_table('bgp_neighbors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('neighbor_ip', sa.String(length=45), nullable=False),
        sa.Column('neighbor_as', sa.Integer(), nullable=False),
        sa.Column('local_as', sa.Integer(), nullable=False),
        sa.Column('state', sa.Enum('IDLE', 'CONNECT', 'ACTIVE', 'OPEN_SENT', 'OPEN_CONFIRM', 'ESTABLISHED', name='bgpstate'), nullable=True),
        sa.Column('admin_status', sa.String(length=20), default='unknown'),
        sa.Column('prefixes_received', sa.Integer(), default=0),
        sa.Column('prefixes_sent', sa.Integer(), default=0),
        sa.Column('messages_received', sa.BigInteger(), default=0),
        sa.Column('messages_sent', sa.BigInteger(), default=0),
        sa.Column('uptime', sa.BigInteger(), default=0),
        sa.Column('last_flap', sa.DateTime(timezone=True), nullable=True),
        sa.Column('flap_count', sa.Integer(), default=0),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('password_enabled', sa.Boolean(), default=False),
        sa.Column('hold_time', sa.Integer(), default=180),
        sa.Column('keepalive_time', sa.Integer(), default=60),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bgp_neighbors_id'), 'bgp_neighbors', ['id'], unique=False)

    # OSPF neighbors table
    op.create_table('ospf_neighbors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('neighbor_ip', sa.String(length=45), nullable=False),
        sa.Column('neighbor_id', sa.String(length=15), nullable=False),
        sa.Column('local_interface', sa.String(length=255), nullable=True),
        sa.Column('local_interface_ip', sa.String(length=45), nullable=True),
        sa.Column('state', sa.Enum('DOWN', 'ATTEMPT', 'INIT', 'TWO_WAY', 'EX_START', 'EXCHANGE', 'LOADING', 'FULL', name='ospfstate'), nullable=True),
        sa.Column('area_id', sa.String(length=15), nullable=True),
        sa.Column('uptime', sa.BigInteger(), default=0),
        sa.Column('dead_timer', sa.Integer(), default=40),
        sa.Column('hello_interval', sa.Integer(), default=10),
        sa.Column('retransmissions', sa.BigInteger(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ospf_neighbors_id'), 'ospf_neighbors', ['id'], unique=False)

    # OSPF processes table
    op.create_table('ospf_processes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('process_id', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.String(length=15), nullable=True),
        sa.Column('admin_status', sa.String(length=20), default='unknown'),
        sa.Column('areas', sa.JSON(), default=list),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # EIGRP neighbors table
    op.create_table('eigrp_neighbors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('neighbor_ip', sa.String(length=45), nullable=False),
        sa.Column('local_interface', sa.String(length=255), nullable=True),
        sa.Column('autonomous_system', sa.Integer(), nullable=False),
        sa.Column('k1', sa.Integer(), default=1),
        sa.Column('k2', sa.Integer(), default=0),
        sa.Column('k3', sa.Integer(), default=1),
        sa.Column('k4', sa.Integer(), default=0),
        sa.Column('k5', sa.Integer(), default=0),
        sa.Column('uptime', sa.BigInteger(), default=0),
        sa.Column('hold_time', sa.Integer(), default=15),
        sa.Column('srtt', sa.Integer(), default=0),
        sa.Column('rto', sa.Integer(), default=0),
        sa.Column('queue_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_eigrp_neighbors_id'), 'eigrp_neighbors', ['id'], unique=False)

    # EIGRP processes table
    op.create_table('eigrp_processes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('autonomous_system', sa.Integer(), nullable=False),
        sa.Column('router_id', sa.String(length=15), nullable=True),
        sa.Column('admin_status', sa.String(length=20), default='unknown'),
        sa.Column('successor_count', sa.Integer(), default=0),
        sa.Column('feasible_successor_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # VPN tunnels table
    op.create_table('vpn_tunnels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('tunnel_name', sa.String(length=255), nullable=False),
        sa.Column('tunnel_interface', sa.String(length=50), nullable=True),
        sa.Column('tunnel_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.Enum('UP', 'DOWN', 'DEGRADED', 'UNKNOWN', name='tunnelstatus'), nullable=True),
        sa.Column('local_endpoint', sa.String(length=45), nullable=True),
        sa.Column('remote_endpoint', sa.String(length=45), nullable=True),
        sa.Column('source_interface', sa.String(length=50), nullable=True),
        sa.Column('ike_version', sa.Integer(), default=2),
        sa.Column('ike_phase1_status', sa.Enum('ACTIVE', 'INACTIVE', 'NEGOTIATING', 'FAILED', name='ikephase1status'), nullable=True),
        sa.Column('ipsec_status', sa.Enum('ACTIVE', 'INACTIVE', 'EXPIRING', 'FAILED', name='ipsecstatus'), nullable=True),
        sa.Column('encryption_algorithm', sa.String(length=50), nullable=True),
        sa.Column('authentication_algorithm', sa.String(length=50), nullable=True),
        sa.Column('bytes_encrypted', sa.BigInteger(), default=0),
        sa.Column('bytes_decrypted', sa.BigInteger(), default=0),
        sa.Column('packets_encrypted', sa.BigInteger(), default=0),
        sa.Column('packets_decrypted', sa.BigInteger(), default=0),
        sa.Column('bytes_dropped', sa.BigInteger(), default=0),
        sa.Column('packets_dropped', sa.BigInteger(), default=0),
        sa.Column('uptime', sa.BigInteger(), default=0),
        sa.Column('last_state_change', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nhrp_peer_type', sa.String(length=20), nullable=True),
        sa.Column('nbma_address', sa.String(length=45), nullable=True),
        sa.Column('tunnel_vrf', sa.String(length=50), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_vpn_tunnels_id'), 'vpn_tunnels', ['id'], unique=False)

    # NHRP cache table
    op.create_table('nhrp_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('protocol_ip', sa.String(length=45), nullable=False),
        sa.Column('nbma_ip', sa.String(length=45), nullable=False),
        sa.Column('tunnel_interface', sa.String(length=50), nullable=True),
        sa.Column('entry_type', sa.String(length=20), default='dynamic'),
        sa.Column('remaining_time', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_nhrp_cache_id'), 'nhrp_cache', ['id'], unique=False)

    # IPSec SA table
    op.create_table('ipsec_sas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tunnel_id', sa.Integer(), sa.ForeignKey('vpn_tunnels.id'), nullable=True),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('sa_index', sa.Integer(), nullable=False),
        sa.Column('direction', sa.String(length=10), nullable=True),
        sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', 'EXPIRING', 'FAILED', name='ipsecstatus'), nullable=True),
        sa.Column('encryption_algorithm', sa.String(length=50), nullable=True),
        sa.Column('authentication_algorithm', sa.String(length=50), nullable=True),
        sa.Column('bytes_processed', sa.BigInteger(), default=0),
        sa.Column('packets_processed', sa.BigInteger(), default=0),
        sa.Column('lifetime_seconds', sa.Integer(), default=28800),
        sa.Column('remaining_seconds', sa.Integer(), default=0),
        sa.Column('lifetime_kb', sa.Integer(), default=4608000),
        sa.Column('remaining_kb', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # Device backups table
    op.create_table('device_backups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('backup_name', sa.String(length=255), nullable=False),
        sa.Column('backup_type', sa.Enum('RUNNING_CONFIG', 'STARTUP_CONFIG', 'FULL', name='backuptype'), nullable=True),
        sa.Column('backup_method', sa.Enum('SSH', 'SCP', 'TFTP', 'SFTP', 'HTTP', name='backupmethod'), nullable=True),
        sa.Column('status', sa.Enum('SUCCESS', 'FAILED', 'IN_PROGRESS', 'SCHEDULED', name='backupstatus'), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('file_size', sa.BigInteger(), default=0),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('git_commit_hash', sa.String(length=40), nullable=True),
        sa.Column('git_branch', sa.String(length=255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_scheduled', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_device_backups_id'), 'device_backups', ['id'], unique=False)

    # Backup schedules table
    op.create_table('backup_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('device_groups.id'), nullable=True),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('frequency', sa.String(length=20), default='daily'),
        sa.Column('cron_expression', sa.String(length=100), nullable=True),
        sa.Column('hour', sa.Integer(), default=2),
        sa.Column('minute', sa.Integer(), default=0),
        sa.Column('day_of_week', sa.Integer(), default=0),
        sa.Column('day_of_month', sa.Integer(), default=1),
        sa.Column('backup_type', sa.Enum('RUNNING_CONFIG', 'STARTUP_CONFIG', 'FULL', name='backuptype'), nullable=True),
        sa.Column('backup_method', sa.Enum('SSH', 'SCP', 'TFTP', 'SFTP', 'HTTP', name='backupmethod'), nullable=True),
        sa.Column('retain_count', sa.Integer(), default=30),
        sa.Column('notify_on_success', sa.Boolean(), default=False),
        sa.Column('notify_on_failure', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # Config changes table
    op.create_table('config_changes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=False),
        sa.Column('backup_id', sa.Integer(), sa.ForeignKey('device_backups.id'), nullable=True),
        sa.Column('change_detected_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('change_type', sa.String(length=50), nullable=True),
        sa.Column('diff_summary', sa.Text(), nullable=True),
        sa.Column('diff_full', sa.Text(), nullable=True),
        sa.Column('detection_method', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # Alerts table
    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('interface_id', sa.Integer(), sa.ForeignKey('interfaces.id'), nullable=True),
        sa.Column('alert_type', sa.Enum('DEVICE_DOWN', 'DEVICE_UP', 'HIGH_CPU', 'HIGH_MEMORY', 'HIGH_BANDWIDTH', 'INTERFACE_DOWN', 'INTERFACE_ERROR', 'BGP_DOWN', 'BGP_FLAP', 'OSPF_DOWN', 'EIGRP_DOWN', 'VPN_DOWN', 'BACKUP_FAILED', 'CONFIG_CHANGED', 'CUSTOM', name='alerttype'), nullable=False),
        sa.Column('severity', sa.Enum('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY', name='alertseverity'), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'SUPPRESSED', name='alertstatus'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('threshold_unit', sa.String(length=50), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=255), nullable=True),
        sa.Column('acknowledgment_note', sa.Text(), nullable=True),
        sa.Column('notification_count', sa.Integer(), default=0),
        sa.Column('notifications_sent', sa.Text(), nullable=True),
        sa.Column('suppressed', sa.Boolean(), default=False),
        sa.Column('suppression_reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_alerts_id'), 'alerts', ['id'], unique=False)

    # Alert rules table
    op.create_table('alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('alert_type', sa.Enum('DEVICE_DOWN', 'DEVICE_UP', 'HIGH_CPU', 'HIGH_MEMORY', 'HIGH_BANDWIDTH', 'INTERFACE_DOWN', 'INTERFACE_ERROR', 'BGP_DOWN', 'BGP_FLAP', 'OSPF_DOWN', 'EIGRP_DOWN', 'VPN_DOWN', 'BACKUP_FAILED', 'CONFIG_CHANGED', 'CUSTOM', name='alerttype'), nullable=False),
        sa.Column('severity', sa.Enum('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY', name='alertseverity'), nullable=True),
        sa.Column('metric', sa.String(length=100), nullable=True),
        sa.Column('operator', sa.String(length=10), nullable=True),
        sa.Column('threshold_value', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), default=0),
        sa.Column('device_ids', sa.Text(), nullable=True),
        sa.Column('group_ids', sa.Text(), nullable=True),
        sa.Column('notify_email', sa.Boolean(), default=False),
        sa.Column('notify_slack', sa.Boolean(), default=False),
        sa.Column('notify_telegram', sa.Boolean(), default=False),
        sa.Column('notify_webhook', sa.Boolean(), default=False),
        sa.Column('webhook_url', sa.String(length=512), nullable=True),
        sa.Column('escalate_after_minutes', sa.Integer(), nullable=True),
        sa.Column('escalate_severity', sa.Enum('INFO', 'WARNING', 'CRITICAL', 'EMERGENCY', name='alertseverity'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # Maintenance windows table
    op.create_table('maintenance_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recurring', sa.Boolean(), default=False),
        sa.Column('recurrence_rule', sa.String(length=100), nullable=True),
        sa.Column('device_ids', sa.Text(), nullable=True),
        sa.Column('alert_types', sa.Text(), nullable=True),
        sa.Column('suppress_notifications', sa.Boolean(), default=True),
        sa.Column('suppress_alert_creation', sa.Boolean(), default=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )

    # Syslog messages table
    op.create_table('syslog_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), sa.ForeignKey('devices.id'), nullable=True),
        sa.Column('facility', sa.Integer(), nullable=True),
        sa.Column('severity', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('hostname', sa.String(length=255), nullable=True),
        sa.Column('tag', sa.String(length=100), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_syslog_messages_id'), 'syslog_messages', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order (due to foreign keys)
    op.drop_table('syslog_messages')
    op.drop_table('maintenance_windows')
    op.drop_table('alert_rules')
    op.drop_table('alerts')
    op.drop_table('config_changes')
    op.drop_table('backup_schedules')
    op.drop_table('device_backups')
    op.drop_table('ipsec_sas')
    op.drop_table('nhrp_cache')
    op.drop_table('vpn_tunnels')
    op.drop_table('eigrp_processes')
    op.drop_table('eigrp_neighbors')
    op.drop_table('ospf_processes')
    op.drop_table('ospf_neighbors')
    op.drop_table('bgp_neighbors')
    op.drop_table('device_health')
    op.drop_table('interfaces')
    op.drop_table('devices')
    op.drop_table('device_groups')
    op.drop_table('audit_logs')
    op.drop_table('users')

    # Drop enums (PostgreSQL specific)
    op.execute('DROP TYPE IF EXISTS alertstatus')
    op.execute('DROP TYPE IF EXISTS alertseverity')
    op.execute('DROP TYPE IF EXISTS alerttype')
    op.execute('DROP TYPE IF EXISTS backupstatus')
    op.execute('DROP TYPE IF EXISTS backupmethod')
    op.execute('DROP TYPE IF EXISTS backuptype')
    op.execute('DROP TYPE IF EXISTS ipsecstatus')
    op.execute('DROP TYPE IF EXISTS ikephase1status')
    op.execute('DROP TYPE IF EXISTS tunnelstatus')
    op.execute('DROP TYPE IF EXISTS ospfstate')
    op.execute('DROP TYPE IF EXISTS bgpstate')
    op.execute('DROP TYPE IF EXISTS devicestatus')
    op.execute('DROP TYPE IF EXISTS devicetype')
    op.execute('DROP TYPE IF EXISTS snmpversion')
    op.execute('DROP TYPE IF EXISTS userrole')
