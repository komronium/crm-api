from datetime import datetime, timedelta, timezone

from app.core import timeutils
from app.models.lead import Lead
from tests.conftest import make_user

LEADS = "/api/v1/leads/"


def new_lead(client, auth, **over):
    data = {"name": "Ali", "phone": "+998901234567"}
    data.update(over)
    return client.post(LEADS, json=data, headers=auth)


# ---------------------------------------------------------------- leads need a signed-in user
def test_every_lead_route_rejects_anonymous_requests(client, admin):
    for method, url in (
        ("get", LEADS), ("get", LEADS + "stats"), ("post", LEADS), ("patch", LEADS + "1"),
        ("delete", LEADS + "1"), ("patch", LEADS + "1/status?status=sale"),
        ("post", LEADS + "1/notes/"), ("delete", LEADS + "notes/1/"),
    ):
        r = getattr(client, method)(url, **({"json": {}} if method in ("post", "patch") else {}))
        assert r.status_code in (401, 403), (method, url, r.status_code)


def test_signed_in_user_can_work_with_leads(client, auth):
    lead = new_lead(client, auth, note="birinchi qo'ng'iroq").json()
    assert lead["name"] == "Ali" and lead["status"] == "new"
    assert client.get(LEADS, headers=auth).json()["new"]["count"] == 1
    assert client.patch(f"{LEADS}{lead['id']}", json={"name": "Vali"}, headers=auth).json()["name"] == "Vali"
    assert client.delete(f"{LEADS}{lead['id']}", headers=auth).status_code == 204


def test_operator_not_only_admin_can_use_leads(client, db):
    make_user(db, "op", "operator-pass-1")
    token = client.post("/api/v1/login", json={"username": "op", "password": "operator-pass-1"}).json()["access_token"]
    assert client.get(LEADS, headers={"Authorization": f"Bearer {token}"}).status_code == 200


# ---------------------------------------------------------------- statuses and input limits
def test_status_must_be_a_known_one(client, auth):
    lead = new_lead(client, auth).json()
    ok = client.patch(f"{LEADS}{lead['id']}/status", params={"status": "sale"}, headers=auth)
    assert ok.status_code == 200 and ok.json()["status"] == "sale"
    bad = client.patch(f"{LEADS}{lead['id']}/status", params={"status": "whatever"}, headers=auth)
    assert bad.status_code == 422


def test_status_of_a_missing_lead_is_404_not_500(client, auth):
    r = client.patch(f"{LEADS}999/status", params={"status": "sale"}, headers=auth)
    assert r.status_code == 404


def test_overlong_or_empty_fields_are_422_not_a_database_error(client, auth):
    assert new_lead(client, auth, name="x" * 129).status_code == 422
    assert new_lead(client, auth, phone="1" * 33).status_code == 422
    assert new_lead(client, auth, name="   ").status_code == 422
    assert new_lead(client, auth, note="n" * 513).status_code == 422
    lead = new_lead(client, auth).json()
    assert client.post(f"{LEADS}{lead['id']}/notes/", json={"text": "t" * 513}, headers=auth).status_code == 422


def test_names_are_trimmed(client, auth):
    assert new_lead(client, auth, name="  Ali  ", phone=" 998901234567 ").json()["name"] == "Ali"


def test_deleting_a_missing_note_is_404(client, auth):
    assert client.delete(f"{LEADS}notes/12345/", headers=auth).status_code == 404


# ---------------------------------------------------------------- accounts
def test_inactive_user_cannot_log_in_and_old_tokens_stop_working(client, db, admin, auth):
    assert client.get("/api/v1/profile/", headers=auth).status_code == 200
    admin.is_active = False
    db.commit()
    assert client.get("/api/v1/profile/", headers=auth).status_code == 401
    r = client.post("/api/v1/login", json={"username": "admin", "password": "admin-pass-1"})
    assert r.status_code == 401


def test_login_is_locked_after_five_wrong_passwords(client, admin):
    for _ in range(5):
        assert client.post("/api/v1/login", json={"username": "admin", "password": "bad"}).status_code == 401
    locked = client.post("/api/v1/login", json={"username": "admin", "password": "admin-pass-1"})
    assert locked.status_code == 429
    # another address is not locked
    other = client.post("/api/v1/login", json={"username": "admin", "password": "admin-pass-1"},
                        headers={"X-Real-IP": "203.0.113.9"})
    assert other.status_code == 200


def test_new_passwords_need_eight_characters(client, auth):
    r = client.post("/api/v1/operators/", json={"username": "op", "password": "short"}, headers=auth)
    assert r.status_code == 422
    r = client.post("/api/v1/operators/", json={"username": "op", "password": "long-enough-1"}, headers=auth)
    assert r.status_code == 201


def test_admin_accounts_cannot_be_deleted(client, db, auth, admin):
    other_admin = make_user(db, "boss2", "boss2-pass-1", is_admin=True)
    assert client.delete(f"/api/v1/operators/{other_admin.id}", headers=auth).status_code == 400
    assert client.delete("/api/v1/profile/", headers=auth).status_code == 400
    op = make_user(db, "op", "operator-pass-1")
    assert client.delete(f"/api/v1/operators/{op.id}", headers=auth).status_code == 204


def test_operators_are_admin_only(client, db):
    make_user(db, "op", "operator-pass-1")
    token = client.post("/api/v1/login", json={"username": "op", "password": "operator-pass-1"}).json()["access_token"]
    assert client.get("/api/v1/operators/", headers={"Authorization": f"Bearer {token}"}).status_code == 403


# ---------------------------------------------------------------- the business day is the Tashkent day
def test_dashboard_day_follows_tashkent_not_utc(client, db, auth):
    # 20:00 UTC on 28 Oct is 01:00 on 29 Oct in Tashkent
    db.add(Lead(name="Night", phone="123", created_at=datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)))
    db.commit()
    on_29 = client.get(LEADS, params={"date_from": "2026-10-29", "date_to": "2026-10-29"}, headers=auth).json()
    on_28 = client.get(LEADS, params={"date_from": "2026-10-28", "date_to": "2026-10-28"}, headers=auth).json()
    assert on_29["new"]["count"] == 1
    assert on_28["new"]["count"] == 0


def test_day_bounds_are_utc_instants_five_hours_earlier():
    from datetime import date
    start = timeutils.day_start(date(2026, 10, 29))
    assert start == datetime(2026, 10, 28, 19, 0, tzinfo=timezone.utc)
    assert timeutils.day_end(date(2026, 10, 29)).date() == date(2026, 10, 29)


def test_stats_count_leads_by_tashkent_day(client, db, auth):
    now = datetime.now(timezone.utc)
    db.add_all([Lead(name="a", phone="1", created_at=now), Lead(name="b", phone="2", created_at=now - timedelta(days=40))])
    db.commit()
    stats = client.get(LEADS + "stats", headers=auth).json()
    assert stats["total"] == 2
    assert sum(p["count"] for p in stats["last_7_days"]) == 1
    assert stats["last_7_days"][-1]["date"] == timeutils.local_today().isoformat()
    assert len(stats["last_12_months"]) == 12 and sum(m["count"] for m in stats["last_12_months"]) == 2


def test_months_back_crosses_year_boundaries():
    from datetime import date
    assert timeutils.months_back(date(2026, 2, 1), 4) == ["2025-11", "2025-12", "2026-01", "2026-02"]


# ---------------------------------------------------------------- Facebook
def test_webhook_verification_uses_facebook_parameter_names(client):
    ok = client.get("/webhook", params={"hub.mode": "subscribe", "hub.challenge": "abc123", "hub.verify_token": "verify-me"})
    assert ok.status_code == 200 and ok.text == "abc123"
    assert client.get("/webhook", params={"hub.mode": "subscribe", "hub.challenge": "x", "hub.verify_token": "nope"}).status_code == 403
    assert client.get("/webhook").status_code == 403


def test_facebook_import_stores_each_lead_and_skips_duplicates(db):
    from app.services.facebook_lead_service import FacebookLeadService
    item = {"id": "L1", "field_data": [{"name": "full_name", "values": ["Ali"]}, {"name": "phone_number", "values": ["+998901"]},
                                       {"name": "kurs", "values": ["ingliz_tili"]}]}
    assert FacebookLeadService._store_lead(db, item) == "created"
    assert FacebookLeadService._store_lead(db, item) == "skipped"
    assert FacebookLeadService._store_lead(db, {"id": "L2", "field_data": []})["reason"] == "missing_name_or_phone"
    lead = db.query(Lead).one()
    assert lead.form_data == [{"question": "Kurs", "answer": "Ingliz tili"}]


def test_polling_detects_an_expired_token():
    from fastapi import HTTPException
    from app.services.facebook_polling import _is_token_error
    exc = HTTPException(502, 'Facebook Graph error: 400 {"error":{"message":"Error validating access token: Session has expired","code":190}}')
    assert _is_token_error(exc)
    assert not _is_token_error(HTTPException(502, "Facebook Graph error: 500 oops"))


def test_api_docs_are_not_public_when_debug_is_off(client):
    for url in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(url).status_code == 404
