"""Settings for regression testing: same app, separate database.

Uses erp/regression.sqlite3 (or the path in the REGRESSION_DB environment
variable), so test data never lands in db.sqlite3.

    DJANGO_SETTINGS_MODULE=erp.settings_regression python manage.py runserver 8001
"""
import os

from .settings import *  # noqa: F401,F403
from .settings import BASE_DIR

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.environ.get("REGRESSION_DB", BASE_DIR / "regression.sqlite3"),
    }
}
