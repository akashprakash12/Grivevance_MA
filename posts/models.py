from django.db import models

class Post(models.Model):
    post_id = models.CharField(max_length=100, unique=True)
    message = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to='post_images/', blank=True, null=True)
    read_comments = models.BooleanField(default=False)
    time_limit = models.FloatField(blank=True, null=True)  # In hours
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post {self.post_id}"