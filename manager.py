import logging
import os
import sys
import asyncio
import threading
from contextlib import asynccontextmanager
# 应用编码修复
import fix_encoding
from fastapi import FastAPI
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from urls import sys_router
import settings
from dataaccess.database import init_db
from biziness.redis_mq import consumer
from multiprocessing import Process

CONSUMER_THREAD_COUNT = settings.CONSUMER_THREAD_COUNT

def run_consumer_in_thread(thread_id):
    """在线程中运行消费者协程"""
    print(f'[consumer-thread-{thread_id}] 启动消费者线程')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(consumer())
    except Exception as e:
        print(f'[consumer-thread-{thread_id}] 消费者异常: {e}')
    finally:
        loop.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    print(f'[lifespan] 启动事件触发，启动 {CONSUMER_THREAD_COUNT} 个消费者线程')
    logging.info(f'[lifespan] 启动事件触发，启动 {CONSUMER_THREAD_COUNT} 个消费者线程')
    
    threads = []
    for i in range(CONSUMER_THREAD_COUNT):
        t = threading.Thread(target=run_consumer_in_thread, args=(i,), daemon=True)
        t.start()
        # p=Process(target=run_consumer_in_thread, args=(i,), daemon=True)
        # p.start()
        # threads.append(t)
    
    print(f'[lifespan] {CONSUMER_THREAD_COUNT} 个消费者线程已启动')
    yield
    # 关闭时执行
    print('[lifespan] 关闭事件触发')

def init_app():
    init_db()

    app = FastAPI(lifespan=lifespan)

    # Session中间件
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=3600 * 24 * 7  # 7天
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    STATIC_DIR = 'static'
    os.makedirs(STATIC_DIR, exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # 包含所有路由（包括权限管理路由已在sys_router中）
    app.include_router(sys_router, prefix='/api', tags=['skills 管理'])

    return app


app = init_app()

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8002)
