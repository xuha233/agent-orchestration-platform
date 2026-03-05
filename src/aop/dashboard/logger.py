"""Dashboard Logger - 内存日志处理器

提供日志存储和检索功能，用于开发者控制台显示。
"""

from __future__ import annotations

import logging
import sys
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LogEntry:
    """日志条目"""
    timestamp: datetime
    level: str
    message: str
    logger_name: str = "root"
    exception: Optional[str] = None


class DashboardLogger(logging.Handler):
    """Dashboard 专用日志处理器

    将日志存储在内存中，供开发者控制台显示。
    """

    MAX_ENTRIES = 500

    def __init__(self, max_entries: int = 500):
        super().__init__()
        self._entries: deque[LogEntry] = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """处理日志记录"""
        try:
            # 获取异常信息
            exception = None
            if record.exc_info:
                exception = self.format(record)

            entry = LogEntry(
                timestamp=datetime.fromtimestamp(record.created),
                level=record.levelname,
                message=record.getMessage(),
                logger_name=record.name,
                exception=exception,
            )

            with self._lock:
                self._entries.append(entry)
        except Exception:
            self.handleError(record)

    def get_entries(
        self,
        level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> list[LogEntry]:
        """获取日志条目

        Args:
            level: 按级别过滤（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            search: 搜索关键词

        Returns:
            过滤后的日志列表（最新的在前面）
        """
        with self._lock:
            entries = list(self._entries)

        # 过滤级别
        if level and level != "ALL":
            entries = [e for e in entries if e.level == level]

        # 搜索
        if search:
            search_lower = search.lower()
            entries = [
                e for e in entries
                if search_lower in e.message.lower()
                or (e.exception and search_lower in e.exception.lower())
            ]

        # 反转顺序，最新的在前面
        return list(reversed(entries))

    def clear(self) -> None:
        """清空日志"""
        with self._lock:
            self._entries.clear()

    def get_count(self) -> int:
        """获取日志条数"""
        with self._lock:
            return len(self._entries)


# 全局实例
_dashboard_logger: Optional[DashboardLogger] = None
_logger_lock = threading.Lock()


def get_dashboard_logger() -> DashboardLogger:
    """获取 Dashboard Logger 实例

    Returns:
        DashboardLogger 实例
    """
    global _dashboard_logger

    with _logger_lock:
        if _dashboard_logger is None:
            _dashboard_logger = DashboardLogger()
            # 设置格式
            _dashboard_logger.setFormatter(logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ))
        return _dashboard_logger


def setup_dashboard_logging() -> None:
    """设置 Dashboard 日志

    将 DashboardLogger 添加到根日志处理器，并捕获所有未处理异常。
    """
    logger = get_dashboard_logger()
    root_logger = logging.getLogger()
    root_logger.addHandler(logger)
    root_logger.setLevel(logging.DEBUG)

    # 设置全局异常捕获，确保所有异常都被记录到 Dashboard
    def handle_exception(exc_type, exc_value, exc_tb):
        """捕获未处理异常并记录到日志"""
        # 先记录到标准日志
        logging.error(
            f"未处理异常: {exc_type.__name__}: {exc_value}",
            exc_info=(exc_type, exc_value, exc_tb)
        )
        # 然后调用原始 excepthook
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = handle_exception
