# CLAUDE.md

## Commands

```bash
# Setup
pip install -Ur requirements.txt
python manage.py makemigrations && python manage.py migrate
python manage.py create_testdata          # seed test data
python manage.py createsuperuser

# Dev server
python manage.py runserver

# Tests
python manage.py test                     # all tests
python manage.py test blog                # single app
coverage run manage.py test               # with coverage

# Static files & search index
python manage.py collectstatic --noinput && python manage.py compress --force
python manage.py build_index              # rebuild Whoosh/ES index

# Docker (full stack: MySQL + Redis + Nginx + app)
docker-compose build && docker-compose up
```

## Architecture

Django 4.2 blog platform, Python 3.10+, MySQL.

### Apps
- **blog** - Core: articles, categories, tags, sidebar, markdown rendering
- **accounts** - Custom user model `BlogUser` (extends AbstractUser), `EmailOrUsernameModelBackend` for login with email or username
- **comments** - Threaded comments with markdown support
- **oauth** - Third-party login (Google, GitHub, Facebook, WeChat/QQ)
- **servermanager** - Admin commands, email testing, WeChat bot (WeRoBot)
- **owntracks** - Location tracking integration
- **amd_cpu** - AMD CPU benchmark data/search

### Key Patterns
- **Caching**: LocMemCache by default; set `DJANGO_REDIS_URL` for Redis. Signal-driven invalidation in `djangoblog/blog_signals.py`. `cache_decorator` in `djangoblog/utils.py` for per-view caching.
- **Search**: Whoosh by default (Chinese segmentation via jieba); set `DJANGO_ELASTICSEARCH_HOST` for Elasticsearch.
- **BlogSettings**: Singleton model (one row enforced in `clean()`), holds site-wide config (title, SEO, analytics, sidebar).
- **i18n**: All URLs wrapped in `i18n_patterns()`.
- **Context processor** (`blog/context_processors.py`): Injects site-wide SEO/nav data into every template (cached).
- **Template tags** (`blog/templatetags/blog_tags.py`): Sidebar widgets, pagination, markdown rendering.

### Key Files
- `djangoblog/settings.py` - Single settings file, env-var driven
- `djangoblog/urls.py` - Root URL config
- `djangoblog/blog_signals.py` - Signal handlers (cache invalidation, email notifications, SEO pings)
- `djangoblog/utils.py` - Shared utilities: `cache_decorator`, `CommonMarkdown`, `get_blog_setting`, `send_email`
- `djangoblog/admin_site.py` - Custom AdminSite (superuser-only access)
- `blog/middleware.py` - OnlineMiddleware (request timing, logging)
- `bin/docker_start.sh` - Docker entrypoint

## Environment Variables

| Variable | Purpose |
|---|---|
| `DJANGO_MYSQL_DATABASE/USER/PASSWORD/HOST/PORT` | MySQL connection |
| `DJANGO_REDIS_URL` | Enables Redis caching (e.g. `redis:6379`) |
| `DJANGO_ELASTICSEARCH_HOST` | Switches search to Elasticsearch |
| `DJANGO_EMAIL_HOST/PORT/USER/PASSWORD` | SMTP email config |
