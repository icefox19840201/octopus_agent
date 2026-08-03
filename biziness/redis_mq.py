import settings
import json
import redis
import os
import traceback
from utils.logger import logger
import asyncio
from mineru.cli.common import do_parse , read_fn
from pathlib import Path
redis_client=redis.Redis(host=settings.redis_mq_host, port=settings.redis_mq_port, db=settings.redis_mq_db, decode_responses=settings.redis_mq_decode_responses)
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
    os.environ.setdefault("MODELSCOPE_CACHE", settings.mineru_model_path)
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

            # doc_file_path = task.get("file_path")
            # print("上传的文件=====》", doc_file_path)
            # pdf_obj = Path(doc_file_path)
            # pdf_bin = read_fn(pdf_obj)
            # do_parse(
            #     output_dir=settings.out_dir,
            #     pdf_file_names=[pdf_obj.stem],
            #     pdf_bytes_list=[pdf_bin],
            #     p_lang_list=["ch"],
            #     backend="pipeline",
            #     parse_method="auto",
            #     formula_enable=True,
            #     table_enable=True,
            #     start_page_id=0,
            #     end_page_id=None,
            # )
            #
            # result_root = Path(settings.out_dir) / pdf_obj.stem / "auto"
            # logger.info(result_root)
            # markdown_path=str(result_root / f"{pdf_obj.stem}.md")
            # json_path=str(result_root / "content_list.json")


        except:
            msg=traceback.format_exc()
            logger.exception(msg)

