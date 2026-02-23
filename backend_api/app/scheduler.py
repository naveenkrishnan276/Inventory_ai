from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


def configure_scheduler(retrain_callable) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(
        retrain_callable,
        trigger=CronTrigger(hour=1, minute=0),
        id="daily_retrain_1am_ist",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
