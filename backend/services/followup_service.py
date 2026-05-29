"""
Follow-up service for automated lead re-engagement.

This module contains the follow-up job that runs hourly via APScheduler.
Implementation of send_first_followup, send_second_followup, and the full
run_followup_job loop is added in Story 4.3.
"""
import logging

logger = logging.getLogger(__name__)


def run_followup_job() -> None:
    """Execute the hourly follow-up job.

    Iterates over active tenants and sends re-engagement messages to
    unresponsive leads. Marks leads as cold after two failed attempts.

    Full implementation added in Story 4.3.
    """
    logger.info("follow_up_job: started (stub — implementation pending Story 4.3)")
