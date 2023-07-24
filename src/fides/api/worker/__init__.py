from loguru import logger

from fides.api.scheduler import MESSAGING_QUEUE_NAME, celery_app
from fides.api.service.saas_request.override_implementations import *


def start_worker() -> None:
    logger.info("Running Celery worker...")
    default_queue_name = celery_app.conf.get("task_default_queue", "celery")
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=info",
            "--concurrency=2",
            f"--queues={default_queue_name},{MESSAGING_QUEUE_NAME}",
        ]
    )


if __name__ == "__main__":  # pragma: no cover
    start_worker()
