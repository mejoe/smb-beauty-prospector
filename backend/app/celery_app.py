from celery import Celery
from app.config import settings

celery_app = Celery(
    "beautyprospector",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.discovery",
        "app.tasks.enrichment",
        "app.tasks.outreach",
        "app.tasks.export",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.discovery.*": {"queue": "discovery"},
        "app.tasks.enrichment.*": {"queue": "enrich"},
        "app.tasks.outreach.*": {"queue": "outreach"},
        "app.tasks.export.*": {"queue": "export"},
    },
    task_default_queue="default",
)
