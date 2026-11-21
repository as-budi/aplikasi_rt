from celery import shared_task

from .services import generate_bills


@shared_task
def generate_monthly_bills(period: str | None = None) -> int:
    return generate_bills(period)
