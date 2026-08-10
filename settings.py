import os
#模板路径
template_dir=os.path.join(os.path.dirname(__file__),"templates")

# PostgreSQL数据库连接配置
DB_USER = "icefox"
DB_PASSWORD = "123456"
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "AI_skill_agent"
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# JWT配置
JWT_SECRET_KEY = "7s9G2kP8zQxL5nBvR7tFdSjHm2cKpAqW1eYrUiO4sDfGhJkLzXcVbNm6"
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 8

#SessionMiddleware配置
SECRET_KEY = "7s9G2kP8zQxL5nBvR7tF1eYrUiO4sDfGhJkLzXcVbNm6"
#redis配置
#短期记忆
redis_uri='redis://127.0.0.1:6379/0'
#skills路径
skills_path=os.path.join(os.path.dirname(__file__),"skills")
#agent配置文件导入路径
config_path=os.path.join(os.path.dirname(__file__),"config")
agent_config_path=os.path.join(config_path,"agent_config")
#文件上传目录
uploads_dir_path=os.path.join(os.path.dirname(__file__),"uploads")
#rag设置
INDEX_DIR=os.path.join(os.path.dirname(__file__),"indexs")
EMBEDINDEX_DIR = os.path.join(INDEX_DIR,'storage') # 向量索引保存目录
os.makedirs(EMBEDINDEX_DIR,exist_ok=True)
BM25_INDEX_DIR = os.path.join(INDEX_DIR,'bm25index')  # BM25 索引保存目录
os.makedirs(BM25_INDEX_DIR,exist_ok=True)
#milvus连接设置
MILVUS_URI = "http://localhost:19530"
MILVUS_USER = "icefox"
MILVUS_PASSWORD = "Pass@word1984"
#向量维度
VECTOR_DIM = 1024
#embedding模型
EMBEDDING_MODEL = r"E:\bigmodel\huggingface_model\embedding\bge-large-zh-v1.5"

#===============redis mq配置
redis_mq_queue_key = "kb_upload_queue"
redis_mq_host="127.0.0.1"
redis_mq_port=6379
redis_mq_db=1
redis_mq_decode_responses=True
#===============redis mq配置结束

#=============rag配置=======================
#mineru模型路径
mineru_model_path = os.path.join(r"E:\bigmodel\modelscope_model",'mineru')
#mineru的输出中路径
out_dir=os.path.join(os.path.dirname(__file__),'rag_output')
os.makedirs(out_dir,exist_ok=True)
#minio配置
minio_remote_addr='127.0.0.1:9100'
mino_access_key = 'admin'
minio_secret_key = 'Admin@123456'
minio_bucket_name = 'rag'
#从minio中下载的文件存放的文件中径
rag_download_temp_dir=os.path.join(uploads_dir_path,'rags')
#上传文件的类型
upload_file_type=['doc','docx','ppt','pptx','xls','xlsx','pdf','txt','md','wav','mp3']
#调用mineru的并发处理数
CONSUMER_THREAD_COUNT = 5
#==============rag配置结束===================