
import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

def func():
    print("Hello")

if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=func, trigger="interval", seconds=1)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    while True:
        print