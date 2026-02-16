from django.contrib import admin

from .models import DailyNote, StudyCheckinSettings, StudySession


class StudyCheckinSettingsAdmin(admin.ModelAdmin):
    list_display = ('checkin_password', 'summary_password', 'daily_target_hours')

    def has_add_permission(self, request):
        if StudyCheckinSettings.objects.exists():
            return False
        return super().has_add_permission(request)


class StudySessionAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'start_time', 'end_time', 'duration_seconds', 'created_at')
    list_filter = ('start_time',)
    search_fields = ('session_key',)
    readonly_fields = ('session_key', 'start_time', 'end_time', 'duration_seconds', 'created_at')


class DailyNoteAdmin(admin.ModelAdmin):
    list_display = ('date', 'content', 'updated_at')
    list_filter = ('date',)
    search_fields = ('content',)
