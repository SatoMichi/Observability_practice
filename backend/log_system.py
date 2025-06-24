"""
JSON構造化ログシステム

このモジュールはアプリケーション全体で使用するJSON形式の
構造化ログ機能を提供します。
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional


class JsonFormatter(logging.Formatter):
    """JSON形式でログを出力するフォーマッター"""
    
    def format(self, record):
        # タイムスタンプをISO 8601形式で追加
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 基本構造
        log_record = {
            "timestamp": timestamp,
            "level": record.levelname,
            "event": getattr(record, 'event_type', 'unknown'),
            "message": record.getMessage()
        }
        
        # 追加フィールドを追加
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 'filename', 
                          'module', 'exc_info', 'exc_text', 'stack_info', 'lineno', 'funcName', 
                          'created', 'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'event_type']:
                log_record[key] = value
        
        return json.dumps(log_record, ensure_ascii=False, default=str)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    JSON構造化ログ用のロガーを設定して返します
    
    Args:
        name: ロガー名
        level: ログレベル (default: INFO)
        
    Returns:
        設定されたロガーインスタンス
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラーをクリア（重複を避けるため）
    logger.handlers.clear()
    
    # ハンドラーの設定
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    
    # 親ロガーへの伝播を無効化（重複を避けるため）
    logger.propagate = False
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    既存のロガーを取得するか、新しいロガーを作成します
    
    Args:
        name: ロガー名 (None の場合はデフォルト名を使用)
        
    Returns:
        ロガーインスタンス
    """
    if name is None:
        name = "app"
    
    return setup_logger(name) 
