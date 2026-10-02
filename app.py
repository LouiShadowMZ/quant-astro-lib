from __future__ import annotations

from pathlib import Path
from flask import Flask, jsonify, render_template, request

from profile_db import ProfileDB
from web_bridge import (
    DEFAULT_SETTINGS,
    calculate_full_chart,
    calculate_partial_chart,
    load_settings,
    public_options,
    safe_json,
)

BASE_DIR = Path(__file__).resolve().parent
USER_DATA_DIR = BASE_DIR / "user_data"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["JSON_AS_ASCII"] = False

# Flask 默认会把返回的 JSON 的键按字母序重排：行星会变成 Ke, Ma, Me, Mo, Ra…，
# 宫头会变成 house 1, house 10, house 11, house 12, house 2…，
# 后端按计算顺序排好的行序到了页面上就全乱了。关掉后，表格行序 = 后端的计算顺序。
app.json.sort_keys = False

settings = load_settings(BASE_DIR / "user_data" / "settings.json")
profile_db = ProfileDB(BASE_DIR / "user_data" / "people.sqlite3")


def ok(data=None, **extra):
    payload = {"ok": True}
    if data is not None:
        payload["data"] = safe_json(data)
    payload.update(safe_json(extra))
    return jsonify(payload)


def fail(message, status=400):
    return jsonify({"ok": False, "error": str(message)}), status


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/bootstrap")
def bootstrap():
    data = {
        "settings": settings,
        "options": public_options(),
        "profiles": profile_db.list_profiles(),
        "profile_fields": profile_db.list_fields(),
    }
    return ok(data, **data)


@app.post("/api/chart/full")
def chart_full():
    try:
        payload = request.get_json(force=True) or {}
        return ok(calculate_full_chart(payload))
    except Exception as exc:
        app.logger.exception("Full chart calculation failed")
        return fail(exc, 400)


@app.post("/api/chart/partial")
def chart_partial():
    try:
        payload = request.get_json(force=True) or {}
        return ok(calculate_partial_chart(payload))
    except Exception as exc:
        app.logger.exception("Partial chart calculation failed")
        return fail(exc, 400)


@app.post("/api/dasha/expand")
def dasha_expand():
    try:
        from quant_astro.dasha_Vimshottari import expand_dasha_interval

        payload = request.get_json(force=True) or {}
        intervals = expand_dasha_interval(
            planet=str(payload["planet"]),
            start=str(payload["start"]),
            duration_seconds=str(payload["duration_seconds"]),
        )
        return ok([item.to_dict(json_safe=True) for item in intervals])
    except Exception as exc:
        app.logger.exception("Dasha expansion failed")
        return fail(exc, 400)


@app.get("/api/profiles")
def list_profiles():
    return ok(profile_db.list_profiles())


@app.get("/api/profiles/<int:profile_id>")
def get_profile(profile_id):
    item = profile_db.get_profile(profile_id)
    if item is None:
        return fail("人物档案不存在。", 404)
    return ok(item)


@app.post("/api/profiles")
def create_profile():
    try:
        payload = request.get_json(force=True) or {}
        return ok(profile_db.create_profile(payload))
    except Exception as exc:
        return fail(exc, 400)


@app.put("/api/profiles/<int:profile_id>")
def update_profile(profile_id):
    try:
        payload = request.get_json(force=True) or {}
        item = profile_db.update_profile(profile_id, payload)
        if item is None:
            return fail("人物档案不存在。", 404)
        return ok(item)
    except Exception as exc:
        return fail(exc, 400)


@app.delete("/api/profiles/<int:profile_id>")
def delete_profile(profile_id):
    if not profile_db.delete_profile(profile_id):
        return fail("人物档案不存在。", 404)
    return ok({"deleted": profile_id})


@app.get("/api/profile-fields")
def list_profile_fields():
    return ok(profile_db.list_fields())


@app.post("/api/profile-fields")
def create_profile_field():
    try:
        payload = request.get_json(force=True) or {}
        return ok(
            profile_db.create_field(
                payload.get("label"),
                bool(payload.get("multiline", False)),
            )
        )
    except Exception as exc:
        return fail(exc, 400)


@app.put("/api/profile-fields/<int:field_id>")
def update_profile_field(field_id):
    try:
        payload = request.get_json(force=True) or {}
        item = profile_db.update_field(field_id, payload)
        if item is None:
            return fail("字段不存在。", 404)
        return ok(item)
    except Exception as exc:
        return fail(exc, 400)


@app.delete("/api/profile-fields/<int:field_id>")
def delete_profile_field(field_id):
    # 同时删除所有档案里这个字段的数据（数据库外键级联）。
    if not profile_db.delete_field(field_id):
        return fail("字段不存在。", 404)
    return ok({"deleted": field_id})


if __name__ == "__main__":
    host = str(settings.get("server", {}).get("host", DEFAULT_SETTINGS["server"]["host"]))
    port = int(settings.get("server", {}).get("port", DEFAULT_SETTINGS["server"]["port"]))
    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True,
    )
