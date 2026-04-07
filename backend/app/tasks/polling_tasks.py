"""Celery tasks for device polling."""
from celery import current_task
from datetime import datetime
import logging

from ..core.celery_config import celery_app
from ..core.database import SessionLocal
from ..models.device import Device, DeviceStatus
from ..services.snmp_service import snmp_service
from ..services.device_health_service import DeviceHealthService
from ..services.routing_service import RoutingService
from ..services.vpn_service import VPNService
from ..services.alert_service import AlertService
from ..models.alert import AlertType, AlertSeverity

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def poll_device_health(self, device_id: int = None):
    """
    Poll device health metrics for all devices or specific device.

    Polls: CPU, Memory, Uptime, Device Status
    """
    db = SessionLocal()
    try:
        # Get devices
        if device_id:
            devices = [db.query(Device).filter(Device.id == device_id).first()]
        else:
            devices = db.query(Device).filter(Device.polling_enabled == True).all()

        health_service = DeviceHealthService(db)
        alert_service = AlertService(db)

        results = {"success": 0, "failed": 0, "devices": []}

        for device in devices:
            if not device:
                continue

            try:
                # Poll health
                health_data = health_service.poll_device_health(device)

                if health_data:
                    health_service.save_device_health(device, health_data)

                    # Check for high CPU alert
                    if health_data.get("cpu_usage", 0) > 90:
                        alert_service.create_alert(
                            alert_type=AlertType.HIGH_CPU,
                            severity=AlertSeverity.CRITICAL,
                            title=f"High CPU Usage - {device.name}",
                            message=f"CPU usage is {health_data['cpu_usage']}%",
                            device=device,
                            threshold_value=90.0,
                            current_value=health_data.get("cpu_usage"),
                        )
                    elif health_data.get("cpu_usage", 0) > 75:
                        alert_service.create_alert(
                            alert_type=AlertType.HIGH_CPU,
                            severity=AlertSeverity.WARNING,
                            title=f"Elevated CPU Usage - {device.name}",
                            message=f"CPU usage is {health_data['cpu_usage']}%",
                            device=device,
                            threshold_value=75.0,
                            current_value=health_data.get("cpu_usage"),
                        )

                    # Check for high memory alert
                    if health_data.get("memory_usage", 0) > 90:
                        alert_service.create_alert(
                            alert_type=AlertType.HIGH_MEMORY,
                            severity=AlertSeverity.CRITICAL,
                            title=f"High Memory Usage - {device.name}",
                            message=f"Memory usage is {health_data['memory_usage']}%",
                            device=device,
                            threshold_value=90.0,
                            current_value=health_data.get("memory_usage"),
                        )

                    results["success"] += 1
                    results["devices"].append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "status": "success",
                    })
                else:
                    # Device unreachable
                    device.status = DeviceStatus.DOWN
                    db.add(device)

                    alert_service.create_alert(
                        alert_type=AlertType.DEVICE_DOWN,
                        severity=AlertSeverity.CRITICAL,
                        title=f"Device Down - {device.name}",
                        message=f"Device {device.name} ({device.ip_address}) is not responding",
                        device=device,
                    )

                    results["failed"] += 1
                    results["devices"].append({
                        "device_id": device.id,
                        "device_name": device.name,
                        "status": "unreachable",
                    })

            except Exception as e:
                logger.error(f"Error polling device {device.id}: {e}")
                results["failed"] += 1
                results["devices"].append({
                    "device_id": device.id,
                    "device_name": device.name,
                    "status": "error",
                    "error": str(e),
                })

        db.commit()
        return results

    except Exception as e:
        logger.error(f"Error in poll_device_health: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def poll_interface_stats(self, device_id: int = None):
    """
    Poll interface statistics for all devices or specific device.

    Polls: In/Out octets, errors, discards, utilization
    """
    db = SessionLocal()
    try:
        if device_id:
            devices = [db.query(Device).filter(Device.id == device_id).first()]
        else:
            devices = db.query(Device).filter(Device.polling_enabled == True).all()

        health_service = DeviceHealthService(db)
        alert_service = AlertService(db)

        results = {"success": 0, "failed": 0, "interfaces_polled": 0}

        for device in devices:
            if not device:
                continue

            try:
                # Poll interfaces
                interface_data = health_service.poll_interfaces(device)

                if interface_data:
                    count = health_service.save_interfaces(device, interface_data)
                    results["interfaces_polled"] += count

                    # Check for interface down alerts
                    for iface in interface_data:
                        if iface.get("oper_status") == "down" and iface.get("admin_status") == "up":
                            alert_service.create_alert(
                                alert_type=AlertType.INTERFACE_DOWN,
                                severity=AlertSeverity.WARNING,
                                title=f"Interface Down - {device.name}",
                                message=f"Interface {iface.get('name')} is down (admin up)",
                                device=device,
                            )

                        # Check for high errors
                        if iface.get("in_errors", 0) > 100 or iface.get("out_errors", 0) > 100:
                            alert_service.create_alert(
                                alert_type=AlertType.INTERFACE_ERROR,
                                severity=AlertSeverity.WARNING,
                                title=f"Interface Errors - {device.name}",
                                message=f"High error count on interface {iface.get('name')}",
                                device=device,
                            )

                    results["success"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(f"Error polling interfaces for device {device.id}: {e}")
                results["failed"] += 1

        db.commit()
        return results

    except Exception as e:
        logger.error(f"Error in poll_interface_stats: {e}")
        raise self.retry(exc=e, countdown=60)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def poll_routing_protocols(self, device_id: int = None):
    """
    Poll routing protocol information for all devices or specific device.

    Polls: BGP neighbors, OSPF neighbors, EIGRP neighbors
    """
    db = SessionLocal()
    try:
        if device_id:
            devices = [db.query(Device).filter(Device.id == device_id).first()]
        else:
            devices = db.query(Device).filter(Device.polling_enabled == True).all()

        routing_service = RoutingService(db)
        alert_service = AlertService(db)

        results = {
            "success": 0,
            "failed": 0,
            "bgp_neighbors": 0,
            "ospf_neighbors": 0,
            "eigrp_neighbors": 0,
        }

        for device in devices:
            if not device:
                continue

            try:
                # Poll all routing protocols
                routing_data = routing_service.poll_all_routing_protocols(device)
                saved = routing_service.save_all_routing_data(device, routing_data)

                results["bgp_neighbors"] += saved.get("bgp_neighbors", 0)
                results["ospf_neighbors"] += saved.get("ospf_neighbors", 0)
                results["eigrp_neighbors"] += saved.get("eigrp_neighbors", 0)

                # Check for BGP neighbor down alerts
                for bgp in routing_data.get("bgp", {}).get("neighbors", []):
                    if bgp.get("state") == "established":
                        continue

                    alert_service.create_alert(
                        alert_type=AlertType.BGP_DOWN,
                        severity=AlertSeverity.CRITICAL,
                        title=f"BGP Neighbor Down - {device.name}",
                        message=f"BGP neighbor {bgp.get('neighbor_ip')} is {bgp.get('state')}",
                        device=device,
                    )

                # Check for OSPF neighbor down alerts
                for ospf in routing_data.get("ospf", {}).get("neighbors", []):
                    if ospf.get("state") == "full":
                        continue

                    alert_service.create_alert(
                        alert_type=AlertType.OSPF_DOWN,
                        severity=AlertSeverity.WARNING,
                        title=f"OSPF Neighbor Issue - {device.name}",
                        message=f"OSPF neighbor {ospf.get('neighbor_ip')} is {ospf.get('state')}",
                        device=device,
                    )

                # Check for EIGRP neighbor down alerts
                for eigrp in routing_data.get("eigrp", {}).get("neighbors", []):
                    # EIGRP neighbors should always be present if configured
                    if not eigrp.get("uptime") or eigrp.get("uptime") < 60:
                        alert_service.create_alert(
                            alert_type=AlertType.EIGRP_DOWN,
                            severity=AlertSeverity.WARNING,
                            title=f"EIGRP Neighbor Issue - {device.name}",
                            message=f"EIGRP neighbor {eigrp.get('neighbor_ip')} has low uptime",
                            device=device,
                        )

                results["success"] += 1

            except Exception as e:
                logger.error(f"Error polling routing for device {device.id}: {e}")
                results["failed"] += 1

        db.commit()
        return results

    except Exception as e:
        logger.error(f"Error in poll_routing_protocols: {e}")
        raise self.retry(exc=e, countdown=120)
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3)
def poll_vpn_status(self, device_id: int = None):
    """
    Poll VPN status for all devices or specific device.

    Polls: IPSec tunnels, GRE tunnels, DMVPN, NHRP cache
    """
    db = SessionLocal()
    try:
        if device_id:
            devices = [db.query(Device).filter(Device.id == device_id).first()]
        else:
            devices = db.query(Device).filter(Device.polling_enabled == True).all()

        vpn_service = VPNService(db)
        alert_service = AlertService(db)

        results = {
            "success": 0,
            "failed": 0,
            "tunnels_polled": 0,
            "nhrp_entries": 0,
        }

        for device in devices:
            if not device:
                continue

            try:
                # Poll VPN data
                vpn_data = vpn_service.poll_all_vpn_data(device)
                saved = vpn_service.save_all_vpn_data(device, vpn_data)

                results["tunnels_polled"] += saved.get("tunnels", 0)
                results["nhrp_entries"] += saved.get("nhrp_cache", 0)

                # Check for tunnel down alerts
                for tunnel in vpn_data.get("tunnels", []):
                    if tunnel.get("status") == "down":
                        alert_service.create_alert(
                            alert_type=AlertType.VPN_DOWN,
                            severity=AlertSeverity.CRITICAL,
                            title=f"VPN Tunnel Down - {device.name}",
                            message=f"Tunnel {tunnel.get('tunnel_name')} is down",
                            device=device,
                        )

                results["success"] += 1

            except Exception as e:
                logger.error(f"Error polling VPN for device {device.id}: {e}")
                results["failed"] += 1

        db.commit()
        return results

    except Exception as e:
        logger.error(f"Error in poll_vpn_status: {e}")
        raise self.retry(exc=e, countdown=120)
    finally:
        db.close()


@celery_app.task
def poll_single_device(device_id: int):
    """
    Poll all metrics from a single device.

    Used for on-demand polling when device is added/updated.
    """
    # Run all polling tasks synchronously for immediate results
    health_result = poll_device_health(device_id=device_id)
    interface_result = poll_interface_stats(device_id=device_id)
    routing_result = poll_routing_protocols(device_id=device_id)
    vpn_result = poll_vpn_status(device_id=device_id)

    return {
        "device_id": device_id,
        "health": health_result,
        "interfaces": interface_result,
        "routing": routing_result,
        "vpn": vpn_result,
    }
