from utils.logger import logger
from config.octopus_enum.status import RagServiceEnum
from pathlib import Path
from mineru.cli.common import do_parse , read_fn
import settings
import os
class RagService:
    @staticmethod
    def know2db(filepath: str):
        #文件扩展名
        file_ex_name_with_mineru=['.doc','.docx','.ppt','.pptx','.xls','.xlsx','.pdf']
        file_ex_name_without_mineru=['.txt','.md']
        file_ex_with_audio=['wav','mp3']
        file_ex=Path(filepath).suffix
        if file_ex in file_ex_name_with_mineru or file_ex in file_ex_name_without_mineru:
            markdown_path=RagService.docs2_markdown(filepath)
            chunk_docs=RagService.chunkdocs(markdown_path)
        elif file_ex in file_ex_with_audio:
            pass
    @staticmethod
    def docs2_markdown(doc_path: str):
        '''
        将文档转为markdown文档（word/excel/pdf/ppt）
        '''
        os.environ.setdefault("MODELSCOPE_CACHE", settings.mineru_model_path)
        doc_obj = Path(doc_path)
        doc_bin = read_fn(doc_obj)
        do_parse(
            output_dir=settings.out_dir,
            pdf_file_names=[doc_obj.stem],
            pdf_bytes_list=[doc_bin],
            p_lang_list=["ch"],
            backend="pipeline",
            parse_method="auto",
            formula_enable=True,
            table_enable=True,
            start_page_id=0,
            end_page_id=None,
        )

        result_root = Path(settings.out_dir) / doc_obj.stem / "auto"
        markdown_path = str(result_root / f"{doc_obj.stem}.md")
        logger.info('markdown_path===={}'.format(markdown_path))
        return markdown_path
    @staticmethod
    def audio2text(markdown_path: str):
        '''
        音频转文本
        '''
        pass
    @staticmethod
    def chunkdocs(doc):
        '''
        文档切片
        '''
        #对文档中的图片提取上传到minio中，在文档中引用
        #切片过程保留表格完整性
        logger.info('进入文档切片流程')

    @staticmethod
    def embeddingdoc2db(doc):
        pass