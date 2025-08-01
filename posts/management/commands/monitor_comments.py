from django.core.management.base import BaseCommand
from posts.views import monitor_complaints
import threading
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Starts the Facebook comment monitoring thread'

    def handle(self, *args, **options):
        logger.info("Starting comment monitoring thread")
        monitor_thread = threading.Thread(target=monitor_complaints)
        monitor_thread.daemon = True  # This makes the thread exit when main thread exits
        monitor_thread.start()