"""
Admin API endpoints — full platform overview, user administration, device assignment, and executive reporting.
Protected by get_current_admin_user dependency (Superuser / ADMIN role required).
"""

from typing import List, Optional
from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.user import User
from app.models.device import Device
from app.models.metric import Metric
from app.models.alert import Alert
from app.schemas.user import UserOut
from app.schemas.device import DeviceOut
from app.services.auth_service import get_current_admin_user
from app.core.security import hash_password

router = APIRouter(prefix="/admin", tags=["Admin Portal"])


# ── Schemas for Admin Operations ──────────────────────────────────────────────
class UserAdminView(BaseModel):
    id: int
    email: str
    full_name: str
    is_active: bool
    is_superuser: bool
    created_at: str
    device_count: int

    model_config = {"from_attributes": True}


class AdminOverview(BaseModel):
    total_users: int
    active_users: int
    total_devices: int
    online_devices: int
    offline_devices: int
    avg_cpu_percent: float
    avg_ram_percent: float
    total_alerts: int
    unresolved_alerts: int


class AssignDeviceRequest(BaseModel):
    user_id: int


class ResetPasswordRequest(BaseModel):
    new_password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get(
    "/overview",
    response_model=AdminOverview,
    summary="Get executive dashboard overview metrics",
)
def get_admin_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Calculates global platform telemetry stats for Executive Admin Portal."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_users = db.query(func.count(User.id)).filter(User.is_active == True).scalar() or 0
    
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    online_devices = db.query(func.count(Device.id)).filter(Device.is_online == True).scalar() or 0
    offline_devices = total_devices - online_devices

    # Latest telemetry averages
    avg_cpu = db.query(func.avg(Metric.cpu_usage_percent)).scalar() or 0.0
    avg_ram = db.query(func.avg(Metric.ram_usage_percent)).scalar() or 0.0

    total_alerts = db.query(func.count(Alert.id)).scalar() or 0
    unresolved_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0

    return AdminOverview(
        total_users=total_users,
        active_users=active_users,
        total_devices=total_devices,
        online_devices=online_devices,
        offline_devices=offline_devices,
        avg_cpu_percent=round(avg_cpu, 1),
        avg_ram_percent=round(avg_ram, 1),
        total_alerts=total_alerts,
        unresolved_alerts=unresolved_alerts,
    )


@router.get(
    "/users",
    response_model=List[UserAdminView],
    summary="List and search all platform users",
)
def list_users(
    q: Optional[str] = Query(None, description="Search by email or name"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Returns all registered users with their endpoint counts."""
    query = db.query(User)
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(User.email.ilike(search_pattern) | User.full_name.ilike(search_pattern))
    
    users = query.all()
    result = []
    for u in users:
        dev_count = db.query(func.count(Device.id)).filter(Device.owner_id == u.id).scalar() or 0
        result.append(
            UserAdminView(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                is_active=u.is_active,
                is_superuser=u.is_superuser,
                created_at=u.created_at.isoformat() if u.created_at else "",
                device_count=dev_count,
            )
        )
    return result


@router.post(
    "/users/{user_id}/toggle-disable",
    response_model=UserAdminView,
    summary="Disable or enable a user account",
)
def toggle_disable_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Toggles a user's is_active status."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Admin cannot disable their own account.")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)

    dev_count = db.query(func.count(Device.id)).filter(Device.owner_id == user.id).scalar() or 0
    return UserAdminView(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at.isoformat() if user.created_at else "",
        device_count=dev_count,
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user account",
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Deletes a user account and unbinds/deletes associated data."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Admin cannot delete their own account.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    db.delete(user)
    db.commit()
    return None


@router.post(
    "/users/{user_id}/reset-password",
    summary="Reset user password",
)
def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Allows Admin to reset password for any user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": f"Password reset successfully for user {user.email}"}


@router.post(
    "/devices/{device_uuid}/assign",
    response_model=DeviceOut,
    summary="Assign a device to a user",
)
def assign_device(
    device_uuid: str,
    payload: AssignDeviceRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Re-assigns ownership of a device to a specific user account."""
    device = db.query(Device).filter(Device.device_uuid == device_uuid).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    device.owner_id = user.id
    db.commit()
    db.refresh(device)
    return device


@router.get(
    "/reports/export",
    summary="Export System Health Audit Report",
)
def export_report(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    """Generates an executive system report JSON for enterprise compliance export."""
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_devices = db.query(func.count(Device.id)).scalar() or 0
    online_devices = db.query(func.count(Device.id)).filter(Device.is_online == True).scalar() or 0
    unresolved_alerts = db.query(func.count(Alert.id)).filter(Alert.is_resolved == False).scalar() or 0

    devices = db.query(Device).all()
    device_summary = [
        {
            "device_uuid": d.device_uuid,
            "hostname": d.hostname,
            "display_name": d.display_name,
            "os_name": d.os_name,
            "is_online": d.is_online,
            "mac_address": d.mac_address,
            "ip_address": d.ip_address,
            "owner_email": d.owner.email if d.owner else "Unassigned",
        }
        for d in devices
    ]

    return {
        "report_title": "InfraMind AI Enterprise Health Audit",
        "generated_by": admin.email,
        "summary": {
            "total_users": total_users,
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "unresolved_alerts": unresolved_alerts,
        },
        "devices": device_summary,
    }
