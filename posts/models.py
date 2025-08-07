# models.py
from django.db import models
from django.utils import timezone
from datetime import datetime

from django.db import models

# models.py updates
class Post(models.Model):
    post_id = models.CharField(max_length=100, unique=True)
    message = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)  # Track when post was last updated
    permalink_url = models.URLField(max_length=500)
    comment_monitoring_end_time = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    time_limit = models.PositiveIntegerField(default=60)
    last_comment_fetch = models.DateTimeField(null=True, blank=True)  # When comments were last fetched

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'comment_monitoring_end_time']),
            models.Index(fields=['post_id']),
        ]

    def __str__(self):
        return f"Post {self.post_id}"

    @property
    def is_monitoring_active(self):
        return self.is_active and self.comment_monitoring_end_time > timezone.now()

    def update_from_facebook(self, fb_data):
        """Update post data from Facebook API response"""
        self.message = fb_data.get('message', self.message)
        if 'created_time' in fb_data:
            self.facebook_created_time = datetime.strptime(
                fb_data['created_time'], '%Y-%m-%dT%H:%M:%S%z'
            )
        self.save()

class Comment(models.Model):
    comment_id = models.CharField(max_length=100, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author_name = models.CharField(max_length=255)
    author_id = models.CharField(max_length=100)
    message = models.TextField()
    created_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]

    def __str__(self):
        return f"Comment {self.comment_id} on Post {self.post.post_id}"