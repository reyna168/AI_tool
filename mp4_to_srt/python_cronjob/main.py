import os
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import socketio

# ── 載入環境變數 ──────────────────────────────────────────────
load_dotenv()

PORT        = int(os.getenv("PORT", 8594))
SOCKET_PORT = int(os.getenv("SOCKETPORT", 8596))
BASE_URL    = os.getenv("BASE_URL", "http://localhost:8594")
TIMEZONE    = os.getenv("TIMEZONE", "Asia/Taipei")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── CORS 允許的來源（正則改用前綴比對）────────────────────────
ALLOWED_ORIGINS_PREFIXES = [
    "http://192.168.",
    "http://172.16.",
    "http://210.61.",
    "http://localhost",
    "http://127.0.0.1",
]

def is_origin_allowed(origin: str) -> bool:
    if not origin:
        return True
    return any(origin.startswith(prefix) for prefix in ALLOWED_ORIGINS_PREFIXES)


# ══════════════════════════════════════════════════════════════
#  Socket.IO 管理器
# ══════════════════════════════════════════════════════════════
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

class SocketManager:
    def __init__(self):
        self.connected_users: dict[str, str] = {}   # userId -> sid

    async def handle_connect(self, sid: str, environ: dict, auth: dict | None):
        # query string 解析
        qs = environ.get("QUERY_STRING", "")
        params = dict(p.split("=") for p in qs.split("&") if "=" in p)
        user_id    = params.get("userId")
        project_id = params.get("projectId")

        if user_id:
            self.connected_users[user_id] = sid

        if project_id:
            await sio.enter_room(sid, project_id)
            logger.info(f"[Socket] User {user_id} joined room: {project_id}")

    async def handle_disconnect(self, sid: str):
        for uid, s in list(self.connected_users.items()):
            if s == sid:
                logger.info(f"[Socket] User disconnected: {uid}")
                del self.connected_users[uid]
                break

    async def handle_send_message(self, sid: str, message: dict):
        project_id       = message.get("projectId")
        task_delegate_id = message.get("taskDelegateId")
        sender           = message.get("sender")
        content          = message.get("content")

        if project_id and sender and content:
            chat_message = {
                "projectId":       project_id,
                "taskDelegateId":  task_delegate_id,
                "sender":          sender,
                "content":         content,
                "timestamp":       message.get("timestamp") or datetime.utcnow().isoformat(),
            }

            # ── 儲存到資料庫（替換成實際 ORM 呼叫）────────────
            try:
                # await prisma.chat_message.create(data=chat_message)
                logger.info(f"[Socket] 訊息已儲存: {chat_message}")
            except Exception as e:
                logger.warning(f"[Socket] 儲存訊息失敗: {e}")

            await sio.emit("receive_message", chat_message, room=project_id)
            logger.info(f"[Socket] 廣播到房間 {project_id}: {chat_message}")

    async def send_notification(self, user_id: str, notification: dict):
        sid = self.connected_users.get(user_id)
        if sid:
            await sio.emit("new_notification", notification, to=sid)


socket_manager = SocketManager()

@sio.event
async def connect(sid, environ, auth=None):
    await socket_manager.handle_connect(sid, environ, auth)

@sio.event
async def disconnect(sid):
    await socket_manager.handle_disconnect(sid)

@sio.event
async def send_message(sid, message):
    await socket_manager.handle_send_message(sid, message)

async def send_notification_to_user(user_id: str, notification: dict):
    await socket_manager.send_notification(user_id, notification)


# ══════════════════════════════════════════════════════════════
#  Webhook / Cron 排程
# ══════════════════════════════════════════════════════════════
async def execute_webhook(url: str, data: dict | None = None):
    payload = {
        "secretKey": os.getenv("LEAVE_UPDATE_SECRET_KEY", ""),
        **(data or {}),
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            logger.info(f"Webhook OK: {url} → {resp.json()}")
    except Exception as e:
        logger.warning(f"Webhook failed: {url} → {e}")


def init_cron_jobs(scheduler: AsyncIOScheduler):
    # ── 每天 00:34 ────────────────────────────────────────────
    async def job_daily_0034():
        await execute_webhook(f"{BASE_URL}/webhooks/attendance", {"timezone": TIMEZONE})
        logger.info("✅ 「出勤表」更新成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/leaveRequest")
        logger.info("✅ 抓取「請假紀錄」成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/business")
        logger.info("✅ 抓取「出差紀錄」成功")

    # ── 每天 08:00 ────────────────────────────────────────────
    async def job_daily_0800():
        await execute_webhook(f"{BASE_URL}/webhooks/purchaseArrival", {"timezone": TIMEZONE})
        logger.info("採購單到貨檢查執行成功")

    # ── 每天 08:20 ────────────────────────────────────────────
    async def job_daily_0820():
        await execute_webhook(f"{BASE_URL}/webhooks/connect/attendance")
        logger.info("打卡API抓取成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/leaveRequest")
        logger.info("✅ 抓取「請假紀錄」成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/business")
        logger.info("✅ 抓取「出差紀錄」成功")

    # ── 每天 12:00 ────────────────────────────────────────────
    async def job_daily_1200():
        await execute_webhook(f"{BASE_URL}/webhooks/connect/attendance")
        logger.info("打卡API 12:00 抓取成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/leaveRequest")
        logger.info("✅ 抓取「請假紀錄」成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/business")
        logger.info("✅ 抓取「出差紀錄」成功")

    # ── 每天 23:58 ────────────────────────────────────────────
    async def job_daily_2358():
        await execute_webhook(f"{BASE_URL}/webhooks/connect/attendance")
        logger.info("打卡API 23:58 抓取成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/overtimeRequest")
        logger.info("✅ 抓取「加班紀錄」成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/leaveRequest")
        logger.info("✅ 抓取「請假紀錄」成功")
        await execute_webhook(f"{BASE_URL}/webhooks/connect/business")
        logger.info("✅ 抓取「出差紀錄」成功")

    # ── 每年 1/1 00:00 ────────────────────────────────────────
    async def job_yearly_new_year():
        await execute_webhook(f"{BASE_URL}/webhooks/leaveBalanceReset")
        logger.info("✅ 「休假」更新成功")

    # ── 每週一 00:01 ──────────────────────────────────────────
    async def job_weekly_monday():
        logger.info("準備轉換值日生....")
        await execute_webhook(f"{BASE_URL}/webhooks/personDuty")
        logger.info("✅ 「值日生」更新成功")

    # ── 每週日 00:01 ──────────────────────────────────────────
    async def job_weekly_sunday():
        logger.info("準備更新寫入上週值日生....")
        await execute_webhook(f"{BASE_URL}/webhooks/personDuty/Sunday")
        logger.info("✅ 寫入「上週值日生」更新成功")

    # ── 每年 7/15 00:00 ───────────────────────────────────────
    async def job_yearly_july():
        await execute_webhook(f"{BASE_URL}/webhooks/companyHolidays")
        logger.info("✅ 「七月匯入新假期」成功")

    # cron 格式: minute, hour, day, month, day_of_week
    scheduler.add_job(job_daily_0034,    "cron", minute=34, hour=0)
    scheduler.add_job(job_daily_0800,    "cron", minute=0,  hour=8)
    scheduler.add_job(job_daily_0820,    "cron", minute=20, hour=8)
    scheduler.add_job(job_daily_1200,    "cron", minute=0,  hour=12)
    scheduler.add_job(job_daily_2358,    "cron", minute=58, hour=23)
    scheduler.add_job(job_yearly_new_year, "cron", minute=0, hour=0, month=1, day=1)
    scheduler.add_job(job_weekly_monday, "cron", minute=1, hour=0, day_of_week="mon")
    scheduler.add_job(job_weekly_sunday, "cron", minute=1, hour=0, day_of_week="sun")
    scheduler.add_job(job_yearly_july,   "cron", minute=0, hour=0, month=7, day=15)


# ══════════════════════════════════════════════════════════════
#  FastAPI 應用程式
# ══════════════════════════════════════════════════════════════
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── 啟動 ──────────────────────────────────────────────────
    # await connect_database()   # 替換成實際資料庫連線
    init_cron_jobs(scheduler)
    scheduler.start()
    logger.info(f"Server running on port {PORT}")
    yield
    # ── 關閉 ──────────────────────────────────────────────────
    scheduler.shutdown()
    # await prisma.disconnect()
    logger.info("Server shutdown complete")


app = FastAPI(
    title="怡良內部系統 - 所有API",
    version="1.0.0",
    description=(
        "✅ 所有時區皆用UTC，資料庫所有時間類別都是儲存UTC時間。\n"
        "✅ Request body所有*紅字標示為必填欄位。"
    ),
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(192\.168|172\.16|210\.61)\.\d+\.\d+.*|^http://localhost.*|^http://127\.0\.0\.1.*",
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

# ── Private Network Access Header ────────────────────────────
@app.middleware("http")
async def add_pna_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

# ── 取得真實 IP ───────────────────────────────────────────────
@app.middleware("http")
async def extract_real_ip(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    request.state.real_ip = ip.lstrip("::ffff:")
    return await call_next(request)

# ── 靜態檔案 ──────────────────────────────────────────────────
app.mount("/public", StaticFiles(directory="public"), name="public")

# ── 掛載 Socket.IO ────────────────────────────────────────────
sio_app = socketio.ASGIApp(sio, other_asgi_app=app)

# ── 路由（替換成實際路由）─────────────────────────────────────
# from src.routes.router import init_web_routers
# init_web_routers(app)

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════
#  啟動入口
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run(
        "main:sio_app",
        host="0.0.0.0",
        port=PORT,
        timeout_keep_alive=600,   # 對應 httpServer.setTimeout(10 * 60 * 1000)
        reload=False,
    )
