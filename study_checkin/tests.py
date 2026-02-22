import json
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase, Client

from .models import DailyNote, StudyCheckinSettings, StudySession


class StudyCheckinSettingsTest(TestCase):
    def test_singleton_enforcement(self):
        StudyCheckinSettings.objects.create(
            checkin_password='pass1',
            summary_password='pass2',
            daily_target_hours=2.0,
        )
        s2 = StudyCheckinSettings(
            checkin_password='pass3',
            summary_password='pass4',
            daily_target_hours=3.0,
        )
        with self.assertRaises(ValidationError):
            s2.clean()

    def test_str(self):
        s = StudyCheckinSettings.objects.create(
            checkin_password='p',
            summary_password='p',
            daily_target_hours=2,
        )
        self.assertEqual(str(s), '学习打卡设置')


class StudySessionTest(TestCase):
    def test_duration_display(self):
        session = StudySession(
            session_key='abc',
            start_time=datetime.now(),
            duration_seconds=3661,
        )
        self.assertEqual(session.duration_display, '1小时1分1秒')

    def test_is_active(self):
        session = StudySession(
            session_key='abc',
            start_time=datetime.now(),
        )
        self.assertTrue(session.is_active)
        session.end_time = datetime.now()
        self.assertFalse(session.is_active)


class PasswordVerificationTest(TestCase):
    def setUp(self):
        self.client = Client()
        StudyCheckinSettings.objects.create(
            checkin_password='test123',
            summary_password='summary456',
            daily_target_hours=2.0,
        )

    def test_correct_checkin_password(self):
        response = self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'test123', 'page': 'checkin'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('session_key', data)
        self.assertIn('study_checkin_auth', response.cookies)

    def test_correct_summary_password(self):
        response = self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'summary456', 'page': 'summary'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('study_summary_auth', response.cookies)

    def test_wrong_password(self):
        response = self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'wrong', 'page': 'checkin'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])


class StudySessionAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        StudyCheckinSettings.objects.create(
            checkin_password='test123',
            summary_password='summary456',
            daily_target_hours=2.0,
        )
        response = self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'test123', 'page': 'checkin'}),
            content_type='application/json',
        )
        self.session_key = response.json()['session_key']

    def test_start_and_end_session(self):
        response = self.client.post(
            '/study/api/start/',
            json.dumps({'session_key': self.session_key}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        session_id = data['session_id']

        response = self.client.post(
            '/study/api/end/',
            json.dumps({
                'session_key': self.session_key,
                'session_id': session_id,
                'duration_seconds': 1800,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        session = StudySession.objects.get(pk=session_id)
        self.assertIsNotNone(session.end_time)
        self.assertLessEqual(session.duration_seconds, 1800)

    def test_cannot_start_duplicate_session(self):
        self.client.post(
            '/study/api/start/',
            json.dumps({'session_key': self.session_key}),
            content_type='application/json',
        )
        response = self.client.post(
            '/study/api/start/',
            json.dumps({'session_key': self.session_key}),
            content_type='application/json',
        )
        data = response.json()
        self.assertFalse(data['success'])

    def test_get_today_sessions(self):
        # Create a session with known duration directly
        StudySession.objects.create(
            session_key=self.session_key,
            start_time=datetime.now() - timedelta(minutes=30),
            end_time=datetime.now(),
            duration_seconds=600,
        )

        response = self.client.get(
            '/study/api/today/',
            {'session_key': self.session_key},
        )
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(len(data['sessions']), 1)
        self.assertEqual(data['total_seconds'], 600)

    def test_unauthorized_start(self):
        response = self.client.post(
            '/study/api/start/',
            json.dumps({'session_key': ''}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_cannot_start_session_from_different_browser(self):
        """A different session_key should not start a session if one is already active"""
        # Start a session with original session_key
        self.client.post(
            '/study/api/start/',
            json.dumps({'session_key': self.session_key}),
            content_type='application/json',
        )
        # Simulate a second browser with a different session_key
        client2 = Client()
        client2.post(
            '/study/api/verify/',
            json.dumps({'password': 'test123', 'page': 'checkin'}),
            content_type='application/json',
        )
        response2 = client2.post(
            '/study/api/start/',
            json.dumps({'session_key': 'different_session_key'}),
            content_type='application/json',
        )
        data = response2.json()
        self.assertFalse(data['success'])

    def test_anti_cheat_duration_cap(self):
        """duration_seconds should not exceed actual elapsed time"""
        session = StudySession.objects.create(
            session_key=self.session_key,
            start_time=datetime.now() - timedelta(seconds=60),
        )
        response = self.client.post(
            '/study/api/end/',
            json.dumps({
                'session_key': self.session_key,
                'session_id': session.pk,
                'duration_seconds': 99999,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        session.refresh_from_db()
        # Should be capped to roughly 60 seconds (with some tolerance)
        self.assertLessEqual(session.duration_seconds, 120)


class SummaryAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        StudyCheckinSettings.objects.create(
            checkin_password='test123',
            summary_password='summary456',
            daily_target_hours=2.0,
        )
        # Authenticate for summary page (sets cookie)
        self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'summary456', 'page': 'summary'}),
            content_type='application/json',
        )

        # Create some test sessions (with any session_key)
        StudySession.objects.create(
            session_key='some_checkin_key',
            start_time=datetime.now() - timedelta(hours=3),
            end_time=datetime.now() - timedelta(hours=2),
            duration_seconds=3600,
        )
        StudySession.objects.create(
            session_key='some_checkin_key',
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_seconds=1800,
        )

    def test_get_summary_data(self):
        response = self.client.get('/study/api/summary-data/')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('today', data)
        self.assertIn('daily', data)
        self.assertIn('monthly', data)
        self.assertEqual(data['today']['total_seconds'], 5400)
        self.assertEqual(len(data['today']['sessions']), 2)
        self.assertGreater(len(data['daily']), 0)
        self.assertGreater(len(data['monthly']), 0)

    def test_summary_unauthorized(self):
        """Summary API should reject requests without cookie"""
        client = Client()  # fresh client, no cookie
        response = client.get('/study/api/summary-data/')
        self.assertEqual(response.status_code, 403)


class PageViewTest(TestCase):
    def test_checkin_page_loads(self):
        response = self.client.get('/study/')
        self.assertEqual(response.status_code, 200)

    def test_summary_page_loads(self):
        response = self.client.get('/study/summary/')
        self.assertEqual(response.status_code, 200)


class DailyNoteTest(TestCase):
    def setUp(self):
        self.client = Client()
        StudyCheckinSettings.objects.create(
            checkin_password='test123',
            summary_password='summary456',
            daily_target_hours=2.0,
        )
        # Authenticate for checkin page
        self.client.post(
            '/study/api/verify/',
            json.dumps({'password': 'test123', 'page': 'checkin'}),
            content_type='application/json',
        )

    def test_save_and_get_note(self):
        # Save
        response = self.client.post(
            '/study/api/note/save/',
            json.dumps({'content': '今天学了数学和英语'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Get
        response = self.client.get('/study/api/note/')
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['content'], '今天学了数学和英语')

    def test_update_note(self):
        # Save first version
        self.client.post(
            '/study/api/note/save/',
            json.dumps({'content': '第一版'}),
            content_type='application/json',
        )
        # Update
        self.client.post(
            '/study/api/note/save/',
            json.dumps({'content': '修改后的版本'}),
            content_type='application/json',
        )
        response = self.client.get('/study/api/note/')
        self.assertEqual(response.json()['content'], '修改后的版本')
        # Should only have one record for today
        self.assertEqual(DailyNote.objects.count(), 1)

    def test_note_unauthorized(self):
        client = Client()  # no cookie
        response = client.post(
            '/study/api/note/save/',
            json.dumps({'content': 'test'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_note_in_summary(self):
        # Save a note
        self.client.post(
            '/study/api/note/save/',
            json.dumps({'content': '学了物理'}),
            content_type='application/json',
        )
        # Create a session so daily data exists
        StudySession.objects.create(
            session_key='key',
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            duration_seconds=3600,
        )
        # Auth for summary
        summary_client = Client()
        summary_client.post(
            '/study/api/verify/',
            json.dumps({'password': 'summary456', 'page': 'summary'}),
            content_type='application/json',
        )
        response = summary_client.get('/study/api/summary-data/')
        data = response.json()
        self.assertEqual(data['today']['note'], '学了物理')
        self.assertEqual(data['daily'][0]['note'], '学了物理')
