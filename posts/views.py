from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse
from .models import Post, Comment
from .facebook_api import FacebookAPI
import os
import threading
import time
import logging
from datetime import datetime, timezone
import json
from django.core.serializers.json import DjangoJSONEncoder

logger = logging.getLogger(__name__)

fb_api = FacebookAPI()
monitor_thread = None
monitor_running = False
last_post_time = None
recent_post_ids = set()

def load_state():
    global last_post_time, recent_post_ids
    state_file = os.path.join(settings.BASE_DIR, 'last_checked_state.json')
    try:
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                last_post_time_value = state.get('last_post_time')
                if last_post_time_value:
                    last_post_time = last_post_time_value
                recent_post_ids.update(state.get('recent_post_ids', []))
                logger.info(f"Loaded state: last_post_time={last_post_time}, recent_post_ids={recent_post_ids}")
    except Exception as e:
        logger.warning(f"Error loading state: {e}")

def save_state():
    global last_post_time, recent_post_ids
    state_file = os.path.join(settings.BASE_DIR, 'last_checked_state.json')
    try:
        with open(state_file, 'w') as f:
            json.dump({
                'last_post_time': last_post_time,
                'recent_post_ids': list(recent_post_ids)
            }, f, indent=2, cls=DjangoJSONEncoder)
        logger.info("State saved successfully")
    except Exception as e:
        logger.error(f"Error saving state: {e}")

def monitor_complaints():
    global last_post_time, recent_post_ids, monitor_running
    logger.info("Starting complaint monitor")
    if not fb_api.validate_token():
        logger.error("Invalid access token")
        monitor_running = False
        return

    while monitor_running:
        try:
            complaint_posts, fetched_post_ids, new_last_post_time = fb_api.get_complaint_posts(last_post_time)
            last_post_time = new_last_post_time
            comments_dict = {}
            for post in complaint_posts:
                if not monitor_running:
                    break
                comments = fb_api.get_comments(post['id'])
                if comments:
                    comments_dict[post['id']] = comments
                time.sleep(0.5)

            # Save posts and comments to database
            for post in complaint_posts:
                post_obj, created = Post.objects.update_or_create(
                    post_id=post['id'],
                    defaults={
                        'message': post.get('message', ''),
                        'permalink_url': post.get('permalink_url', ''),
                        'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                        'comment_count': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                        'created_at': datetime.strptime(post['created_time'], '%Y-%m-%dT%H:%M:%S%z'),
                        'is_deleted': False,
                    }
                )
                if created:
                    recent_post_ids.add(post['id'])
                for comment in comments_dict.get(post['id'], []):
                    Comment.objects.update_or_create(
                        comment_id=comment['id'],
                        post=post_obj,
                        defaults={
                            'author_name': comment.get('from', {}).get('name', 'Unknown'),
                            'author_id': comment.get('from', {}).get('id', ''),
                            'message': comment.get('message', ''),
                            'created_at': datetime.strptime(comment['created_time'], '%Y-%m-%dT%H:%M:%S%z'),
                            'likes': comment.get('like_count', 0),
                            'comment_count': comment.get('comment_count', 0),
                        }
                    )

            # Mark deleted posts
            Post.objects.exclude(post_id__in=fetched_post_ids).update(is_deleted=True)
            logger.info(f"Marked {Post.objects.filter(is_deleted=True).count()} posts as deleted")

            # Save to Excel
            fb_api.write_comments_to_excel(complaint_posts, comments_dict)
            recent_post_ids.difference_update(set(Post.objects.exclude(post_id__in=fetched_post_ids).values_list('post_id', flat=True)))
            recent_post_ids = set(list(recent_post_ids)[-50:])
            save_state()

        except Exception as e:
            logger.error(f"Error in monitor cycle: {e}")
        time.sleep(30)

def start_monitor():
    global monitor_thread, monitor_running
    if not monitor_running:
        monitor_running = True
        monitor_thread = threading.Thread(target=monitor_complaints)
        monitor_thread.daemon = True
        monitor_thread.start()
        logger.info("Monitor thread started")

def stop_monitor():
    global monitor_running
    monitor_running = False
    logger.info("Monitor thread stopped")

def index(request):
    start_monitor()
    context = {}
    if request.method == 'POST':
        message = request.POST.get('message', '')
        image = request.FILES.get('file') if 'file' in request.FILES else None
        if not message and not image:
            context['error'] = 'Message or file is required'
            return render(request, 'posts/index.html', context)

        if '#complaint' not in message.lower():
            message += ' #complaint'

        image_path = None
        if image:
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}
            if image.name.rsplit('.', 1)[1].lower() in allowed_extensions:
                image_path = os.path.join(settings.MEDIA_ROOT, 'post_images', image.name)
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                with open(image_path, 'wb+') as f:
                    for chunk in image.chunks():
                        f.write(chunk)
            else:
                context['error'] = 'Unsupported file type'
                return render(request, 'posts/index.html', context)

        response = fb_api.post_to_page(message, image_path)
        if response and 'id' in response:
            Post.objects.create(
                post_id=response['id'],
                message=message,
                read_comments=True,
                created_at=datetime.now(timezone.utc),
                permalink_url=f"https://www.facebook.com/{response['id']}",
                likes=0,
                comment_count=0,
                is_deleted=False
            )
            context['success'] = f"Successfully posted! Post ID: {response['id']}"
            return render(request, 'posts/index.html', context)
        context['error'] = 'Failed to post'
        return render(request, 'posts/index.html', context)

    return render(request, 'posts/index.html', context)

def manage_posts(request):
    posts = Post.objects.filter(is_deleted=False)
    return render(request, 'posts/manage_posts.html', {'posts': posts})

def edit_post(request, post_id):
    try:
        post = Post.objects.get(post_id=post_id, is_deleted=False)
    except Post.DoesNotExist:
        return render(request, 'posts/edit_post.html', {'error': 'Post not found'})

    if request.method == 'POST':
        message = request.POST.get('message', '')
        if not message:
            return render(request, 'posts/edit_post.html', {'post': post, 'error': 'Message is required'})

        if '#complaint' not in message.lower():
            message += ' #complaint'

        response = fb_api.update_post(post_id, message)
        if response and 'success' in response:
            post.message = message
            post.save()
            return redirect('manage_posts')
        return render(request, 'posts/edit_post.html', {'post': post, 'error': 'Failed to update post'})

    return render(request, 'posts/edit_post.html', {'post': post})

def delete_post(request, post_id):
    try:
        post = Post.objects.get(post_id=post_id, is_deleted=False)
    except Post.DoesNotExist:
        return redirect('manage_posts')

    if request.method == 'POST':
        response = fb_api.delete_post(post_id)
        post.is_deleted = True
        post.save()
        return redirect('manage_posts')

    return render(request, 'posts/manage_posts.html', {'posts': Post.objects.filter(is_deleted=False)})