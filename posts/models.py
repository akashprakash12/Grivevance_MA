from django.db import models

class Post(models.Model):
    post_id = models.CharField(max_length=100, unique=True)
    message = models.TextField(blank=True, null=True)
    image = models.FileField(upload_to='post_images/', blank=True, null=True)
    read_comments = models.BooleanField(default=False)
    time_limit = models.FloatField(blank=True, null=True)  # In hours
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)
    permalink_url = models.URLField(max_length=500, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)  # New field

    def __str__(self):
        return f"Post {self.post_id}"

class Comment(models.Model):
    comment_id = models.CharField(max_length=100, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author_name = models.CharField(max_length=255, blank=True, null=True)
    author_id = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    likes = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)

    def __str__(self):
        return f"Comment {self.comment_id} on Post {self.post.post_id}"