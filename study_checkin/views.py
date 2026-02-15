import json
import uuid
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST, require_GET

from .models import StudyCheckinSettings, StudySession


def get_study_settings():
    """获取学习打卡单例配置，首次访问时自动创建默认配置"""
    value = cache.get('study_checkin_settings')
    if value:
        return value
    value = StudyCheckinSettings.objects.first()
    if not value:
        value = StudyCheckinSettings.objects.create(
            checkin_password='study123',
            summary_password='summary123',
            daily_target_hours=2.0,
        )
    cache.set('study_checkin_settings', value, 3600)
    return value


def check_study_auth(request, page='checkin'):
    """检查请求是否携带有效的认证 cookie"""
    cookie_name = f'study_{page}_auth'
    return request.COOKIES.get(cookie_name)


def checkin_view(request):
    """打卡计时页面"""
    session_key = check_study_auth(request, 'checkin')
    settings = get_study_settings()

    # 检查是否有未结束的会话
    active_session = None
    if session_key:
        active_session = StudySession.objects.filter(
            session_key=session_key, end_time__isnull=True
        ).first()

    active_session_data = None
    if active_session:
        elapsed = (datetime.now() - active_session.start_time).total_seconds()
        active_session_data = {
            'id': active_session.pk,
            'start_time': active_session.start_time.strftime('%H:%M:%S'),
            'elapsed_seconds': int(elapsed),
        }

    return render(request, 'study_checkin/checkin.html', {
        'authenticated': bool(session_key),
        'session_key': session_key or '',
        'daily_target_hours': float(settings.daily_target_hours),
        'active_session': json.dumps(active_session_data),
    })


def summary_view(request):
    """统计汇总页面"""
    session_key = check_study_auth(request, 'summary')
    return render(request, 'study_checkin/summary.html', {
        'authenticated': bool(session_key),
    })


@require_POST
def verify_password(request):
    """验证密码并设置认证 cookie"""
    data = json.loads(request.body)
    password = data.get('password', '')
    page = data.get('page', 'checkin')

    settings = get_study_settings()

    if page == 'checkin':
        correct = settings.checkin_password
    else:
        correct = settings.summary_password

    if password == correct:
        session_key = uuid.uuid4().hex
        response = JsonResponse({'success': True, 'session_key': session_key})
        cookie_name = f'study_{page}_auth'
        response.set_cookie(
            cookie_name, session_key,
            max_age=30 * 24 * 3600,
            httponly=True,
            samesite='Lax',
        )
        return response
    else:
        return JsonResponse({'success': False, 'error': '密码错误'}, status=403)


@require_POST
def start_session(request):
    """开始一个新的学习会话"""
    data = json.loads(request.body)
    session_key = data.get('session_key', '')
    if not session_key:
        return JsonResponse({'success': False, 'error': '未授权'}, status=403)

    # 检查是否有未结束的会话
    active = StudySession.objects.filter(
        session_key=session_key, end_time__isnull=True
    ).first()
    if active:
        return JsonResponse({
            'success': False,
            'error': '已有进行中的学习会话',
            'session_id': active.pk,
        })

    session = StudySession.objects.create(
        session_key=session_key,
        start_time=datetime.now(),
    )
    return JsonResponse({
        'success': True,
        'session_id': session.pk,
        'start_time': session.start_time.strftime('%H:%M:%S'),
    })


@require_POST
def end_session(request):
    """结束一个学习会话"""
    data = json.loads(request.body)
    session_key = data.get('session_key', '')
    session_id = data.get('session_id')
    duration_seconds = data.get('duration_seconds', 0)

    try:
        session = StudySession.objects.get(pk=session_id, session_key=session_key)
    except StudySession.DoesNotExist:
        return JsonResponse({'success': False, 'error': '会话不存在'}, status=404)

    session.end_time = datetime.now()

    # 防作弊：duration 不能超过实际经过的时间
    max_duration = (session.end_time - session.start_time).total_seconds()
    duration_seconds = min(int(duration_seconds), int(max_duration))

    session.duration_seconds = duration_seconds
    session.save()
    return JsonResponse({'success': True})


@require_GET
def get_today_sessions(request):
    """获取今日所有已完成的学习会话"""
    session_key = request.GET.get('session_key', '')
    if not session_key:
        return JsonResponse({'success': False, 'error': '未授权'}, status=403)

    today = datetime.now().date()
    sessions = StudySession.objects.filter(
        session_key=session_key,
        start_time__date=today,
        end_time__isnull=False,
    )
    total_seconds = sum(s.duration_seconds for s in sessions)
    sessions_data = [{
        'id': s.pk,
        'start_time': s.start_time.strftime('%H:%M'),
        'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
        'duration_seconds': s.duration_seconds,
        'duration_display': s.duration_display,
    } for s in sessions]

    return JsonResponse({
        'success': True,
        'sessions': sessions_data,
        'total_seconds': total_seconds,
    })


@require_GET
def get_summary_data(request):
    """获取统计汇总数据（单学生模式，查询所有记录）"""
    # 验证统计页面认证 cookie
    if not check_study_auth(request, 'summary'):
        return JsonResponse({'success': False, 'error': '未授权'}, status=403)

    today = datetime.now().date()
    base_qs = StudySession.objects.filter(end_time__isnull=False)

    # 今日会话
    today_sessions = base_qs.filter(start_time__date=today)
    today_total = sum(s.duration_seconds for s in today_sessions)
    today_data = [{
        'start_time': s.start_time.strftime('%H:%M'),
        'end_time': s.end_time.strftime('%H:%M'),
        'duration_seconds': s.duration_seconds,
        'duration_display': s.duration_display,
    } for s in today_sessions]

    # 每日汇总（最近30天）
    daily = base_qs.filter(
        start_time__date__gte=today - timedelta(days=30),
    ).values(
        date=TruncDate('start_time')
    ).annotate(
        total_seconds=Sum('duration_seconds')
    ).order_by('-date')

    daily_data = [{
        'date': d['date'].strftime('%Y-%m-%d'),
        'total_seconds': d['total_seconds'],
        'hours': round(d['total_seconds'] / 3600, 1),
    } for d in daily]

    # 月度汇总
    monthly = base_qs.values(
        month=TruncMonth('start_time')
    ).annotate(
        total_seconds=Sum('duration_seconds')
    ).order_by('-month')

    monthly_data = [{
        'month': m['month'].strftime('%Y-%m'),
        'total_seconds': m['total_seconds'],
        'hours': round(m['total_seconds'] / 3600, 1),
    } for m in monthly]

    return JsonResponse({
        'success': True,
        'today': {
            'sessions': today_data,
            'total_seconds': today_total,
        },
        'daily': daily_data,
        'monthly': monthly_data,
        'daily_target_hours': float(get_study_settings().daily_target_hours),
    })
