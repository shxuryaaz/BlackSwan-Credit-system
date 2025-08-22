from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Celery configuration
celery_app = Celery(
    "credtech_workers",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    include=[
        "tasks_ingest_structured",
        "tasks_ingest_unstructured", 
        "tasks_score_compute",
        "tasks_ingest_yfinance",
        "tasks_ingest_news_rss"
    ]
)

# Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    broker_connection_retry_on_startup=True,
    result_expires=3600,  # 1 hour
)

# Task routing
celery_app.conf.task_routes = {
    "tasks_ingest_structured.*": {"queue": "structured"},
    "tasks_ingest_unstructured.*": {"queue": "unstructured"},
    "tasks_score_compute.*": {"queue": "scoring"},
    # "tasks_retrain.*": {"queue": "ml"},  # TODO: Implement retraining tasks
}

if __name__ == "__main__":
    celery_app.start()
