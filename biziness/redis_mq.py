import settings
import json
import redis
import traceback
from utils.logger import logger
import asyncio
redis_client=redis.Redis(host=settings.redis_mq_host, port=settings.redis_mq_port, db=settings.redis_mq_db, decode_responses=settings.redis_mq_decode_responses)
async def producer(filepath):
    try:
        task = {
            "file_path": filepath
        }

        redis_client.lpush(settings.redis_mq_queue_key, json.dumps(task))
        print("任务已入队")
        return True
    except:
        msg=traceback.format_exc()
        logger.exception(msg)
        return False

async def consumer():
    while True:
        try:
            pop_res= redis_client.brpop(settings.redis_mq_queue_key, timeout=1)
            if pop_res is None:
                logger.info('队列为空，消费端正常运行')
                await asyncio.sleep(3)
                continue
            _, data = pop_res
            task = json.loads(data)
            print("收到上传任务：", task.get("file_path", "未知文件"))
            doc_file_path = task.get("file_path")
            print("上传的文件=====》", doc_file_path)

        except:
            msg=traceback.format_exc()
            logger.exception(msg)

