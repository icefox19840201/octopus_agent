import logging
import sys
import gzip
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "octopus_agent.log"


class CompressedRotatingFileHandler(TimedRotatingFileHandler):
    """
    按天轮转的日志处理器，支持压缩旧日志
    当日志文件达到指定大小时，会压缩打包
    """

    def __init__(self, filename, when='midnight', interval=1, backupCount=30,
                 encoding='utf-8', delay=False, utc=False, maxBytes=10*1024*1024):
        self.maxBytes = maxBytes
        self.current_file_size = 0
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc)

    def emit(self, record):
        """
        重写emit方法，检查文件大小并在需要时压缩
        """
        if self.stream is None:
            self.stream = self._open()

        # 检查当前文件大小
        if self.stream:
            self.stream.flush()
            current_size = self.stream.tell() if hasattr(self.stream, 'tell') else 0

            # 如果超过大小限制，进行压缩轮转
            if current_size >= self.maxBytes:
                self.doRollover()

        super().emit(record)

    def doRollover(self):
        """
        重写轮转方法，添加压缩功能
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # 获取当前时间戳
        current_time = datetime.now()
        timestamp = current_time.strftime("%Y%m%d_%H%M%S")

        # 构建压缩文件名
        base_name = Path(self.baseFilename).stem
        compressed_name = f"{base_name}_{timestamp}.log.gz"
        compressed_path = LOG_DIR / compressed_name

        # 压缩当前日志文件
        if Path(self.baseFilename).exists():
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 清空原日志文件
            with open(self.baseFilename, 'w', encoding=self.encoding) as f:
                pass

        # 清理旧的压缩文件
        self._cleanup_old_logs()

        # 重新打开日志文件
        if not self.delay:
            self.stream = self._open()

    def _cleanup_old_logs(self):
        """
        清理超过保留期限的旧日志文件
        """
        if self.backupCount <= 0:
            return

        cutoff_date = datetime.now() - timedelta(days=self.backupCount)
        base_name = Path(self.baseFilename).stem

        for log_file in LOG_DIR.glob(f"{base_name}_*.log.gz"):
            try:
                # 从文件名提取日期
                file_stem = log_file.stem  # skillagent_20250115_120000
                parts = file_stem.split('_')
                if len(parts) >= 3:
                    date_str = parts[-2]  # 20250115
                    file_date = datetime.strptime(date_str, "%Y%m%d")

                    if file_date < cutoff_date:
                        log_file.unlink()
                        print(f"已删除旧日志: {log_file.name}")
            except Exception as e:
                print(f"清理旧日志时出错 {log_file.name}: {e}")


class SafeRotatingFileHandler(RotatingFileHandler):
    """
    安全的按大小轮转日志处理器，支持压缩
    """

    def __init__(self, filename, maxBytes=10*1024*1024, backupCount=30,
                 encoding='utf-8', delay=False):
        self.compressed_backupCount = backupCount
        super().__init__(filename, maxBytes=maxBytes, backupCount=backupCount,
                         encoding=encoding, delay=delay)

    def doRollover(self):
        """
        重写轮转方法，压缩旧日志文件
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # 压缩最旧的备份文件
        for i in range(self.backupCount - 1, 0, -1):
            sfn = f"{self.baseFilename}.{i}.gz"
            dfn = f"{self.baseFilename}.{i + 1}.gz"

            if Path(sfn).exists():
                if i == self.backupCount - 1:
                    Path(sfn).unlink()
                else:
                    shutil.move(sfn, dfn)

        # 压缩当前日志文件
        dfn = f"{self.baseFilename}.1.gz"
        if Path(self.baseFilename).exists():
            with open(self.baseFilename, 'rb') as f_in:
                with gzip.open(dfn, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 清空原日志文件
            with open(self.baseFilename, 'w', encoding=self.encoding) as f:
                pass

        # 清理超过保留期限的旧日志
        self._cleanup_old_logs()

        if not self.delay:
            self.stream = self._open()

    def _cleanup_old_logs(self):
        """
        清理超过30天的旧压缩日志
        """
        cutoff_date = datetime.now() - timedelta(days=30)
        base_name = Path(self.baseFilename).name

        for log_file in LOG_DIR.glob(f"{base_name}.*.gz"):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
            except Exception as e:
                print(f"清理旧日志时出错 {log_file.name}: {e}")


# 配置日志格式
_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s.%(funcName)s:%(lineno)d - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# 创建按天轮转的日志处理器（每天午夜轮转，保留30天，达到10MB时压缩）
_file_handler = CompressedRotatingFileHandler(
    LOG_FILE,
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8',
    maxBytes=10*1024*1024  # 10MB
)
_file_handler.setFormatter(_formatter)
_file_handler.setLevel(logging.DEBUG)

# 控制台处理器
_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_formatter)
_console_handler.setLevel(logging.INFO)


def get_logger(name: str = "octopus_agent") -> logging.Logger:
    """获取配置好的日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加处理器
    if not logger.handlers:
        logger.addHandler(_file_handler)
        logger.addHandler(_console_handler)

    return logger


# 默认日志实例
logger = get_logger("octopus_agent")


def get_log_stats():
    """
    获取日志统计信息
    """
    stats = {
        "log_dir": str(LOG_DIR),
        "current_log": str(LOG_FILE),
        "current_log_size": 0,
        "compressed_logs": [],
        "total_compressed_size": 0
    }

    # 当前日志文件大小
    if LOG_FILE.exists():
        stats["current_log_size"] = LOG_FILE.stat().st_size

    # 压缩日志文件
    base_name = LOG_FILE.stem
    for log_file in LOG_DIR.glob(f"{base_name}_*.log.gz"):
        try:
            file_stat = log_file.stat()
            stats["compressed_logs"].append({
                "name": log_file.name,
                "size": file_stat.st_size,
                "mtime": datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
            stats["total_compressed_size"] += file_stat.st_size
        except Exception as e:
            print(f"获取日志统计信息时出错: {e}")

    stats["compressed_count"] = len(stats["compressed_logs"])

    return stats


def cleanup_logs(days: int = 30):
    """
    手动清理指定天数之前的日志
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    deleted_count = 0
    deleted_size = 0

    base_name = LOG_FILE.stem

    # 清理压缩日志
    for log_file in LOG_DIR.glob(f"{base_name}_*.log.gz"):
        try:
            file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if file_mtime < cutoff_date:
                file_size = log_file.stat().st_size
                log_file.unlink()
                deleted_count += 1
                deleted_size += file_size
        except Exception as e:
            print(f"清理日志时出错 {log_file.name}: {e}")

    logger.info(f"日志清理完成: 删除 {deleted_count} 个文件, 释放 {deleted_size / 1024 / 1024:.2f} MB")

    return {
        "deleted_count": deleted_count,
        "deleted_size_mb": deleted_size / 1024 / 1024
    }
