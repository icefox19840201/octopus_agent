import settings
import json
import redis
import os
import traceback
import requests
from urllib.parse import quote, urlparse, urlunparse
from utils.logger import logger
import asyncio
from pathlib import Path
from biziness.rag_service import RagService

redis_client=redis.Redis(host=settings.redis_mq_host, port=settings.redis_mq_port,
                         db=settings.redis_mq_db, decode_responses=settings.redis_mq_decode_responses)
async def producer(filepath):
    '''
    redis生产端
    '''
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
    '''
    redis 消费端
    '''
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
            #下载文件到临时目录
            download_temp_dir=settings.rag_download_temp_dir
            os.makedirs(download_temp_dir, exist_ok=True)

            #下载
            file_url = task.get("file_path")
            parsed = urlparse(file_url)
            encoded_path = quote(parsed.path)
            encoded_url = urlunparse(parsed._replace(path=encoded_path))
            file_name = Path(parsed.path).name
            local_file_path = os.path.join(download_temp_dir, file_name)
            response = requests.get(encoded_url, timeout=60)
            response.raise_for_status()

            with open(local_file_path, 'wb') as f:
                f.write(response.content)
            doc_file_path = local_file_path
            RagService.know2db(doc_file_path, encoded_url)
            os.remove(local_file_path)

        except:
            msg=traceback.format_exc()
            logger.exception(msg)

