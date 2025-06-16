from django.shortcuts import render, redirect
from django.conf import settings
from .models import Post
from grievance.facebook_api import FacebookAPI
import os
import threading
import time
from django.http import JsonResponse

fb_api = FacebookAPI()

def index(request):
    if request.method == 'POST':
        message = request.POST.get('message')
        image = request.FILES.get('image') if 'image' in request.FILES else None
        read_comments = 'read_comments' in request.POST
        time_limit = float(request.POST.get('time_limit', 0)) if request.POST.get('time_limit') else None
        image_path = None
        if image:
            image_path = os.path.join(settings.BASE_DIR, 'media', 'post_images', image.name)
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            with open(image_path, 'wb+') as f:
                for chunk in image.chunks():
                    f.write(chunk)
        response = fb_api.post_to_page(message, image_path)
        if 'id' in response:
            post = Post.objects.create(
                post_id=response['id'],
                message=message,
                read_comments=read_comments,
                time_limit=time_limit
            )
            if read_comments:
                threading.Thread(target=read_comments_thread, args=(post,)).start()
            return redirect('index')
        return render(request, 'posts/index.html', {'error': 'Failed to post'})
    return render(request, 'posts/index.html', {'posts': Post.objects.all()})

def read_comments_thread(post):
    end_time = time.time() + (post.time_limit * 3600 if post.time_limit else float('inf'))
    while time.time() < end_time and post.read_comments:
        comments = fb_api.get_comments(post.post_id, post.time_limit)
        fb_api.write_comments_to_excel(post.post_id, comments)
        time.sleep(600)  # Poll every 10 minutes

def get_comments_status(request):
    posts = Post.objects.filter(read_comments=True)
    status = {post.post_id: {
        'post_id': post.post_id,
        'message': post.message,
        'reading': post.read_comments,
        'time_limit': post.time_limit
    } for post in posts}
    return JsonResponse(status)