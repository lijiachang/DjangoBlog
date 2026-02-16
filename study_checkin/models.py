from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now


class StudyCheckinSettings(models.Model):
    """学习打卡配置（单例模式）"""
    checkin_password = models.CharField(
        '打卡页面密码',
        max_length=128,
        help_text='学生访问打卡页面所需密码'
    )
    summary_password = models.CharField(
        '统计页面密码',
        max_length=128,
        help_text='访问统计汇总页面所需密码'
    )
    daily_target_hours = models.DecimalField(
        '每日学习目标(小时)',
        max_digits=4,
        decimal_places=1,
        default=2.0,
        help_text='达到此时长后显示提醒'
    )

    class Meta:
        verbose_name = '学习打卡设置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return '学习打卡设置'

    def clean(self):
        if StudyCheckinSettings.objects.exclude(id=self.id).count():
            raise ValidationError('只能有一条配置记录')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        from django.core.cache import cache
        cache.delete('study_checkin_settings')


class StudySession(models.Model):
    """学习会话记录"""
    session_key = models.CharField(
        '会话标识',
        max_length=64,
        db_index=True,
    )
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(
        '学习时长(秒)',
        default=0,
        help_text='实际学习时长（扣除暂停时间）'
    )
    created_at = models.DateTimeField('创建时间', default=now)

    class Meta:
        verbose_name = '学习记录'
        verbose_name_plural = verbose_name
        ordering = ['-start_time']

    def __str__(self):
        end = self.end_time.strftime('%H:%M') if self.end_time else '进行中'
        return f"{self.start_time.strftime('%Y-%m-%d %H:%M')} - {end}"

    @property
    def duration_display(self):
        h, remainder = divmod(self.duration_seconds, 3600)
        m, s = divmod(remainder, 60)
        return f"{h}小时{m}分{s}秒"

    @property
    def is_active(self):
        return self.end_time is None


class DailyNote(models.Model):
    """每日学习总结"""
    date = models.DateField('日期', unique=True)
    content = models.TextField('今日总结', blank=True, default='')
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '每日总结'
        verbose_name_plural = verbose_name
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} 总结"
