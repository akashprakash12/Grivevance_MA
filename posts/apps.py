from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class PostsConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField' # Changed from 'django.db.AutoField'
    name = 'posts'

    def ready(self):
        # This will run when Django starts
        import sys
        if 'runserver' in sys.argv:
            logger.info("Runserver detected - starting comment monitoring")
            from django.core.management import call_command
            call_command('monitor_comments')