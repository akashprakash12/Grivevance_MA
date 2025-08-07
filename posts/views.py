from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse, HttpResponse, FileResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Post, Comment
from posts.facebook_api import FacebookAPI
import os
import threading
import time
import logging
from datetime import datetime, timezone, timedelta
import pandas as pd
import json
from django.core.serializers.json import DjangoJSONEncoder
from posts.classi import classify_facebook_comment, save_grievances_to_excel


logger = logging.getLogger(__name__)

fb_api = FacebookAPI()
monitor_thread = None
monitor_running = False

@login_required
def index(request):
    global monitor_running
    if not monitor_running:
        start_monitor()
    
    context = {}
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        image_file = request.FILES.get('file')
        time_limit = float(request.POST.get('monitor_duration', 60))

        if not message and not image_file:
            context['error'] = 'Message or image is required'
            return render(request, 'posts/index.html', context)

        if '#complaint' not in message.lower():
            message += ' #complaint'

        image_path = None
        if image_file:
            allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.mp4', '.mov', '.avi'}
            file_ext = os.path.splitext(image_file.name)[1].lower()
            
            if file_ext not in allowed_extensions:
                context['error'] = 'Unsupported file type. Please upload images (PNG, JPG, GIF) or videos (MP4, MOV, AVI)'
                return render(request, 'posts/index.html', context)
            
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            image_path = os.path.join(temp_dir, image_file.name)
            
            with open(image_path, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)

        try:
            response = fb_api.post_to_page(message, image_path)
            
            if response and 'id' in response:
                post_id = response['id']
                if '_' not in post_id:
                    post_id = f"{fb_api.page_id}_{post_id}"
                
                post = Post.objects.create(
                    post_id=post_id,
                    message=message,
                    image=image_file if image_file else None,
                    created_at=datetime.now(timezone.utc),
                    permalink_url=f"https://www.facebook.com/{post_id}",
                    comment_monitoring_end_time=datetime.now(timezone.utc) + timedelta(minutes=time_limit),
                    is_active=True,
                    time_limit=time_limit
                )
                
                context['success'] = f"Successfully posted! Post ID: {post_id}"
                return render(request, 'posts/index.html', context)
            else:
                context['error'] = 'Failed to post: No response from Facebook API'
            
        except Exception as e:
            logger.error(f"Failed to post: {str(e)}", exc_info=True)
            context['error'] = f'Failed to post: {str(e)}'
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                except Exception as e:
                    logger.error(f"Error deleting temp file: {str(e)}")
    
    return render(request, 'posts/index.html', context)

@login_required
def manage_posts(request):
    posts = Post.objects.filter(is_deleted=False).order_by('-created_at')
    now = datetime.now(timezone.utc)
    return render(request, 'posts/manage_posts.html', {
        'posts': posts,
        'now': now
    })

@login_required
def edit_post(request, post_id):
    try:
        post = Post.objects.get(post_id=post_id)
    except Post.DoesNotExist:
        return render(request, 'posts/edit_post.html', {'error': 'Post not found'})

    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        time_limit = float(request.POST.get('monitor_duration', 60))

        try:
            monitor_end_time = post.created_at + timedelta(minutes=time_limit)
            
            response = fb_api.update_post(post.post_id, message)
            if not response or not response.get('success'):
                raise Exception("Failed to update post message on Facebook")

            post.message = message
            post.comment_monitoring_end_time = monitor_end_time
            post.time_limit = time_limit
            post.is_active = True
            post.save()

            return redirect('posts:manage_posts')
        except Exception as e:
            logger.error(f"Error updating post: {str(e)}", exc_info=True)
            return render(request, 'posts/edit_post.html', {
                'post': post,
                'error': f'Failed to update post: {str(e)}',
                'time_limit': time_limit,
                'monitor_end_time': monitor_end_time.strftime('%Y-%m-%dT%H:%M')
            })

    remaining_time = (post.comment_monitoring_end_time - post.created_at).total_seconds() / 60
    return render(request, 'posts/edit_post.html', {
        'post': post,
        'time_limit': round(remaining_time),
        'monitor_end_time': post.comment_monitoring_end_time.strftime('%Y-%m-%dT%H:%M')
    })

@login_required
@require_POST
def delete_post(request, post_id):
    try:
        if request.POST.get('confirmation') != 'true':
            return JsonResponse({'status': 'error', 'message': 'Confirmation required'}, status=400)
            
        post = Post.objects.get(post_id=post_id)
        
        # First mark as inactive in our system
        post.is_active = False
        post.is_deleted = True
        post.save()
        
        # Then try to delete from Facebook
        fb_response = fb_api.delete_post(post_id)
        
        # Consider successful if:
        # 1. Facebook confirms deletion, OR
        # 2. We get a permission error (post exists but we can't access), OR
        # 3. The post is already gone (error code 100)
        success = False
        fb_error = None
        
        if fb_response:
            if fb_response.get('success'):
                success = True
            elif 'error' in fb_response:
                error_code = fb_response['error'].get('code')
                if error_code in [10, 100]:  # Permission error or doesn't exist
                    success = True
                fb_error = fb_response['error'].get('message', 'Unknown Facebook error')
        
        if success:
            return JsonResponse({'status': 'success'})
        else:
            error_msg = fb_error or 'Failed to delete post from Facebook'
            return JsonResponse({
                'status': 'partial_success', 
                'message': f'Post removed from system but Facebook deletion may have failed: {error_msg}'
            })
            
    except Post.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Post not found'}, status=404)
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Failed to delete post: {str(e)}'}, status=500)

@login_required
def get_comments(request, post_id):
    try:
        post = Post.objects.get(post_id=post_id, is_active=True)
    except Post.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Post not found'}, status=404)

    if post.comment_monitoring_end_time < datetime.now(timezone.utc):
        return JsonResponse({'status': 'error', 'message': 'Comment reading period expired'}, status=400)

    comments = fb_api.get_comments(post_id)
    new_comments = []

    for comment in comments:
        new_comments.append({
            'id': comment['id'],
            'name': comment['user'],
            'message': comment['message'],
            'created_time': comment['created_time'].strftime('%Y-%m-%dT%H:%M:%S%z')
        })

    return JsonResponse({'status': 'success', 'comments': new_comments})

@login_required
def download_excel(request, post_id):
    excel_path = os.path.join(settings.BASE_DIR, 'comments', 'comments.xlsx')
    if not os.path.exists(excel_path):
        return HttpResponse('No comments found', status=404)

    with open(excel_path, 'rb') as f:
        response = FileResponse(
            f,
            as_attachment=True,
            filename=f"comments_{post_id}.xlsx",
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    return response

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

def monitor_complaints():
    """Continuously monitors Facebook posts for new comments and processes them"""
    logger.info("Starting Facebook comment monitoring service")

    while True:
        try:
            now = datetime.now(timezone.utc)
            
            # Get active posts that still need monitoring
            active_posts = Post.objects.filter(
                is_active=True,
                comment_monitoring_end_time__gt=now,
                is_deleted=False
            ).order_by('-created_at')

            if not active_posts.exists():
                logger.debug("No active posts to monitor - sleeping for 60 seconds")
                time.sleep(60)
                continue

            logger.info(f"Monitoring {active_posts.count()} active posts")
            
            for post in active_posts:
                try:
                    if post.is_deleted:
                        post.is_active = False
                        post.save()
                        continue
                        
                    # Get new comments since last check
                    comments = fb_api.get_comments(post.post_id, post.last_comment_fetch)
                    
                    if comments:
                        new_comments_count = 0
                        grievances = []
                        
                        for comment in comments:
                            try:
                                # Classify and create grievance data
                                grievance_data = classify_facebook_comment(comment['message'])
                                
                                if 'error' in grievance_data:
                                    logger.error(f"Classification failed for comment {comment['id']}: {grievance_data['error']}")
                                    continue
                                
                                # Add Facebook metadata
                                grievance_data.update({
                                    'facebook_comment_id': comment['id'],
                                    'facebook_post_id': post.post_id,
                                    'facebook_user_id': comment.get('author_id', ''),
                                    'comment_date': comment['created_time'].strftime('%Y-%m-%d %H:%M:%S')
                                })
                                
                                grievances.append(grievance_data)
                                
                                # Save original comment to database
                                _, created = Comment.objects.update_or_create(
                                    comment_id=comment['id'],
                                    post=post,
                                    defaults={
                                        'author_name': comment['user'],
                                        'author_id': comment['author_id'],
                                        'message': comment['message'],
                                        'created_at': comment['created_time'],
                                    }
                                )
                                if created:
                                    new_comments_count += 1
                                    
                            except Exception as e:
                                logger.error(f"Error processing comment {comment.get('id')}: {str(e)}")
                                continue
                        
                        if grievances:
                            # Save classified grievances to Excel
                            excel_success = save_grievances_to_excel(grievances)
                            if excel_success:
                                logger.info(f"Saved {len(grievances)} grievances to Excel")
                        
                        if new_comments_count > 0:
                            post.last_comment_fetch = now
                            post.save()
                    
                    # Check if monitoring period has ended
                    if post.comment_monitoring_end_time <= now:
                        post.is_active = False
                        post.save()
                        logger.info(f"Monitoring ended for post: {post.post_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing post {post.post_id}: {str(e)}")
                    continue
            
            # Sleep between monitoring cycles
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"Critical error in monitor cycle: {str(e)}", exc_info=True)
            time.sleep(60)
