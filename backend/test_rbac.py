import requests
import uuid

API = "http://127.0.0.1:8000/api/v1"

def test_rbac():
    # 1. Register users (ignore if already exist)
    requests.post(f"{API}/auth/register", json={"email": "admin2@test.com", "password": "password", "full_name": "Admin Two"})
    requests.post(f"{API}/auth/register", json={"email": "usera@test.com", "password": "password", "full_name": "User A"})
    requests.post(f"{API}/auth/register", json={"email": "userb@test.com", "password": "password", "full_name": "User B"})

    # Set admin2 role in DB directly for test
    import sqlite3
    conn = sqlite3.connect("inframind.db")
    c = conn.cursor()
    c.execute("UPDATE users SET role='ADMIN' WHERE email='admin2@test.com'")
    conn.commit()
    conn.close()

    # Login
    tok_admin = requests.post(f"{API}/auth/login", json={"email": "admin2@test.com", "password": "password"}).json()["access_token"]
    tok_a = requests.post(f"{API}/auth/login", json={"email": "usera@test.com", "password": "password"}).json()["access_token"]
    tok_b = requests.post(f"{API}/auth/login", json={"email": "userb@test.com", "password": "password"}).json()["access_token"]

    def auth(token): return {"Authorization": f"Bearer {token}"}

    # Register devices
    uid_admin = str(uuid.uuid4())
    uid_a = str(uuid.uuid4())
    uid_b = str(uuid.uuid4())

    requests.post(f"{API}/devices/register", json={
        "device_uuid": uid_admin, "hostname": "admin-pc", "os_name": "Windows", "os_version": "11", "architecture": "amd64", "agent_version": "1.0.0"
    }, headers=auth(tok_admin))

    requests.post(f"{API}/devices/register", json={
        "device_uuid": uid_a, "hostname": "usera-pc", "os_name": "Windows", "os_version": "11", "architecture": "amd64", "agent_version": "1.0.0"
    }, headers=auth(tok_a))

    requests.post(f"{API}/devices/register", json={
        "device_uuid": uid_b, "hostname": "userb-pc", "os_name": "Windows", "os_version": "11", "architecture": "amd64", "agent_version": "1.0.0"
    }, headers=auth(tok_b))

    # Send Telemetry
    for u, tok in [(uid_admin, tok_admin), (uid_a, tok_a), (uid_b, tok_b)]:
        requests.post(f"{API}/metrics/ingest", json={
            "device_uuid": u, "timestamp_utc": "2023-10-10T00:00:00", "cpu_usage_percent": 10.0
        }, headers=auth(tok))

    # VERIFY ADMIN
    admin_devices = requests.get(f"{API}/admin/devices", headers=auth(tok_admin)).json()
    assert any(d["device_uuid"] == uid_a for d in admin_devices), "Admin should see User A device"
    assert any(d["device_uuid"] == uid_b for d in admin_devices), "Admin should see User B device"

    # VERIFY USER A
    a_devices = requests.get(f"{API}/devices/", headers=auth(tok_a)).json()
    assert any(d["device_uuid"] == uid_a for d in a_devices), "User A should see their device"
    assert not any(d["device_uuid"] == uid_b for d in a_devices), "User A MUST NOT see User B device"

    # Verify 403 on cross-tenant access
    res = requests.get(f"{API}/devices/{uid_b}", headers=auth(tok_a))
    assert res.status_code == 403, f"User A should get 403 when accessing User B device, got {res.status_code}"

    # Verify metric access
    res2 = requests.get(f"{API}/metrics/{uid_b}/latest", headers=auth(tok_a))
    assert res2.status_code == 403, f"User A should get 403 when accessing User B metrics, got {res2.status_code}"

    # Verify Admin Metric access
    res3 = requests.get(f"{API}/admin/telemetry/{uid_a}/latest", headers=auth(tok_admin))
    assert res3.status_code == 200, f"Admin should get 200 when accessing User A metrics via admin api, got {res3.status_code}"

    print("ALL TESTS PASSED SUCCESSFULLY! ✅")

if __name__ == "__main__":
    test_rbac()
