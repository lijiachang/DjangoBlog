"""
Redis 运行一段时间后偶尔报错：You can't write against a read only replica.

进入 read-only 模式（通常是 RDB 持久化失败导致 stop-writes-on-bgsave-error 触发）。
此时所有 cache.set() / cache.delete() 调用抛出 ReadOnlyError，导致页面 500 错误。重启 Redis 后恢复。
整个项目有 12 个文件使用 cache.get/set/delete，全部没有 try/except 保护。
修复方案
创建一个容错 Redis 缓存后端，继承 Django 的 RedisCache，捕获所有 Redis 异常后静默降级（cache miss / no-op）。只需改两个文件，零改动现有业务代码。

效果：Redis 故障时页面正常加载（只是没有缓存加速），不再 500。

这个修复方案不保证解决问题
"""

import logging

from django.core.cache.backends.redis import RedisCache

logger = logging.getLogger(__name__)


class SafeRedisCache(RedisCache):
    """Redis 缓存后端，捕获连接/只读等异常，降级为缓存未命中。

    当 Redis 出现 ReadOnlyError、ConnectionError 等故障时，
    不会抛出异常导致页面 500，而是静默降级（跳过缓存）。
    """

    def get(self, key, default=None, version=None):
        try:
            return super().get(key, default, version)
        except Exception:
            logger.warning("Redis cache get failed for key: %s", key)
            return default

    def set(self, *args, **kwargs):
        try:
            return super().set(*args, **kwargs)
        except Exception:
            logger.warning("Redis cache set failed")

    def delete(self, *args, **kwargs):
        try:
            return super().delete(*args, **kwargs)
        except Exception:
            logger.warning("Redis cache delete failed")

    def clear(self):
        try:
            return super().clear()
        except Exception:
            logger.warning("Redis cache clear failed")

    def has_key(self, *args, **kwargs):
        try:
            return super().has_key(*args, **kwargs)
        except Exception:
            return False

    def get_many(self, *args, **kwargs):
        try:
            return super().get_many(*args, **kwargs)
        except Exception:
            return {}

    def set_many(self, *args, **kwargs):
        try:
            return super().set_many(*args, **kwargs)
        except Exception:
            return []

    def delete_many(self, *args, **kwargs):
        try:
            return super().delete_many(*args, **kwargs)
        except Exception:
            pass

    def incr(self, key, delta=1, version=None):
        try:
            return super().incr(key, delta, version)
        except Exception:
            return None
