# server.py
# Web wrapper cho locketgold.py — KHÔNG sửa file gốc
import os
import asyncio
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

# Import các hàm từ file gốc
# File gốc có if __name__ == "__main__" nên import sẽ không kích hoạt main()
import locketgold as core

API_KEY = os.environ.get("API_KEY", "").strip()
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def render(template_name, **ctx):
    tpl = env.get_template(template_name)
    return web.Response(text=tpl.render(**ctx), content_type="text/html")

def check_api_key(request):
    if not API_KEY:
        return True  # Nếu chưa đặt API_KEY, cho phép tất cả (không khuyến nghị)
    key = request.headers.get("X-API-Key") or request.query.get("key", "")
    return key == API_KEY

async def handle_index(request):
    key = request.query.get("key", "")
    authed = (not API_KEY) or (key == API_KEY)
    return render("index.html", authed=authed, api_key_set=bool(API_KEY))

async def handle_inject(request):
    if not check_api_key(request):
        return web.json_response({"error": "Unauthorized"}, status=401)

    try:
        data = await request.json()
    except Exception:
        data = {}

    username = (data.get("username") or request.query.get("username", "")).strip()
    if not username:
        return web.json_response({"error": "Thiếu username"}, status=400)

    # Gọi đúng logic từ file gốc
    uid = await core.resolve_uid(username)
    if not uid:
        return web.json_response({"error": "Không tìm thấy UID"}, status=404)

    result = await core.inject_gold(uid, core.TOKEN_CONFIG)

    # Lấy trạng thái sau khi inject
    status = await core.check_status(uid)

    return web.json_response({
        "username": username,
        "uid": uid,
        "success": bool(result),
        "status": status,
    })

async def handle_health(request):
    return web.Response(text="OK")

def create_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/inject", handle_inject)
    app.router.add_get("/health", handle_health)
    return app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    web.run_app(create_app(), host="0.0.0.0", port=port)
