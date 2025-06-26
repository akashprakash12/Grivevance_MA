import requests
from django.conf import settings
import time
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from datetime import datetime, timedelta, timezone
import os
import pandas as pd
import logging
from posts.models import Post

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('facebook_realtime.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FacebookAPI:
    def __init__(self):
        self.access_token = settings.FB_ACCESS_TOKEN
        self.page_id = settings.FB_PAGE_ID
        self.base_url = 'https://graph.facebook.com/v20.0'
        self.excel_file = os.path.join(settings.BASE_DIR, 'comments', 'comments.xlsx')
        os.makedirs(os.path.dirname(self.excel_file), exist_ok=True)
        self.max_comments_per_post = 100
        self.max_cell_chars = 32767
        self.max_retries = 3
        self.retry_delay = 5
        self.api_timeout = 30

    def validate_token(self):
        url = f"{self.base_url}/me?access_token={self.access_token}"
        response = self.make_api_request(url)
        if response and 'id' in response:
            logger.info("Access token validated successfully")
            return True
        logger.error(f"Access token validation failed. Response: {response}")
        return False

    def make_api_request(self, url, params=None, method='GET', data=None, files=None):
        for attempt in range(self.max_retries):
            try:
                if method == 'POST':
                    response = requests.post(url, params=params, data=data, files=files, timeout=self.api_timeout)
                elif method == 'DELETE':
                    response = requests.delete(url, params=params, timeout=self.api_timeout)
                else:
                    response = requests.get(url, params=params, timeout=self.api_timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP Error: {e}, Response: {e.response.text}")
                if e.response.status_code == 429:
                    retry_after = int(e.response.headers.get('Retry-After', self.retry_delay))
                    logger.warning(f"Rate limited. Retrying after {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue
                return None
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(self.retry_delay * (attempt + 1))
        logger.error(f"Failed to make API request after {self.max_retries} attempts")
        return None

    def post_to_page(self, message=None, image_path=None):
        if not image_path:
            url = f"{self.base_url}/{self.page_id}/feed"
            params = {'access_token': self.access_token}
            data = {'message': message or ''}
        else:
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext in {'.png', '.jpg', '.jpeg', '.gif'}:
                url = f"{self.base_url}/{self.page_id}/photos"
                params = {'access_token': self.access_token, 'message': message or ''}
                files = {'source': open(image_path, 'rb')}
            elif file_ext in {'.mp4', '.mov', '.avi'}:
                url = f"https://graph-video.facebook.com/v20.0/{self.page_id}/videos"
                params = {'access_token': self.access_token, 'description': message or ''}
                files = {'source': open(image_path, 'rb')}
            else:
                logger.error(f"Unsupported file type: {file_ext}")
                return None
            response = self.make_api_request(url, params=params, method='POST', files=files)
            files['source'].close()
            return response

        response = self.make_api_request(url, params=params, method='POST', data=data)
        if response and 'id' in response:
            logger.info(f"Successfully posted: Post ID={response['id']}")
        return response

    def update_post(self, post_id, message):
        url = f"{self.base_url}/{post_id}"
        params = {'access_token': self.access_token}
        data = {'message': message}
        response = self.make_api_request(url, params=params, method='POST', data=data)
        if response and 'success' in response:
            logger.info(f"Successfully updated post: Post ID={post_id}")
        return response

    def delete_post(self, post_id):
        url = f"{self.base_url}/{post_id}"
        params = {'access_token': self.access_token}
        response = self.make_api_request(url, params=params, method='DELETE')
        if response and 'success' in response:
            logger.info(f"Successfully deleted post: Post ID={post_id}")
        return response

    def get_complaint_posts(self, last_post_time=None):
        url = f"{self.base_url}/{self.page_id}/posts"
        params = {
            'fields': 'id,created_time,message,permalink_url,likes.summary(true),comments.summary(true)',
            'access_token': self.access_token,
            'limit': 10
        }
        data = self.make_api_request(url, params)
        if not data or 'data' not in data:
            logger.warning("No post data returned from API")
            return [], set(), last_post_time

        complaint_posts = []
        fetched_post_ids = set()
        current_latest_time = last_post_time

        for post in data['data']:
            post_time = post['created_time']
            if not current_latest_time or post_time > current_latest_time:
                current_latest_time = post_time
            fetched_post_ids.add(post['id'])
            if post.get('message', '').lower().find('#complaint') != -1:
                complaint_posts.append(post)
                logger.info(f"Found #complaint post: ID={post['id']}")

        return complaint_posts, fetched_post_ids, current_latest_time

    def get_comments(self, post_id):
        url = f"{self.base_url}/{post_id}/comments"
        params = {
            'fields': 'id,created_time,from{name,id},message,comment_count,like_count',
            'access_token': self.access_token,
            'limit': self.max_comments_per_post,
            'order': 'chronological'
        }
        comments = []
        while url:
            data = self.make_api_request(url, params if url.endswith('/comments') else None)
            if not data or 'data' not in data:
                break
            for comment in data['data']:
                comments.append(comment)
            url = data.get('paging', {}).get('next', None)
            params = None
            time.sleep(0.5)
        logger.info(f"Found {len(comments)} comments for post {post_id}")
        return comments

    def write_comments_to_excel(self, posts, comments_dict):
        columns = [
            'Type', 'ID', 'Author', 'Author ID', 'Time', 'Content',
            'URL', 'Parent ID', 'Parent Content', 'Likes', 'Comment Count'
        ]
        new_data = []
        # Get deleted post IDs
        deleted_post_ids = set(Post.objects.filter(is_deleted=True).values_list('post_id', flat=True))
        # Only include posts that are not deleted
        for post in posts:
            if post['id'] not in deleted_post_ids:
                new_data.append({
                    'Type': 'Post',
                    'ID': post['id'],
                    'Author': 'Page',
                    'Author ID': self.page_id,
                    'Time': post['created_time'],
                    'Content': post.get('message', '[No text]'),
                    'URL': post.get('permalink_url', ''),
                    'Parent ID': '',
                    'Parent Content': '',
                    'Likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                    'Comment Count': post.get('comments', {}).get('summary', {}).get('total_count', 0)
                })
                # Only include comments for non-deleted posts
                for comment in comments_dict.get(post['id'], []):
                    new_data.append({
                        'Type': 'Comment',
                        'ID': comment['id'],
                        'Author': comment.get('from', {}).get('name', 'Unknown'),
                        'Author ID': comment.get('from', {}).get('id', ''),
                        'Time': comment['created_time'],
                        'Content': comment.get('message', '[No text]'),
                        'URL': f"{post.get('permalink_url', '')}?comment_id={comment['id']}",
                        'Parent ID': post['id'],
                        'Parent Content': post.get('message', '')[:50] + '...' if post.get('message') else '',
                        'Likes': comment.get('like_count', 0),
                        'Comment Count': comment.get('comment_count', 0)
                    })

        df_new = pd.DataFrame(new_data, columns=columns)
        df_new['Time'] = pd.to_datetime(df_new['Time'], errors='coerce', utc=True)
        df_new['Content'] = df_new['Content'].apply(lambda x: str(x)[:self.max_cell_chars] if pd.notna(x) else '')
        df_new['Parent Content'] = df_new['Parent Content'].apply(lambda x: str(x)[:self.max_cell_chars] if pd.notna(x) else '')

        file_exists = os.path.exists(self.excel_file)
        if file_exists:
            df_existing = pd.read_excel(self.excel_file)
            df_existing['Time'] = pd.to_datetime(df_existing['Time'], errors='coerce', utc=True)
            # Filter out deleted posts and their comments
            df_existing = df_existing[
                (~df_existing['ID'].isin(deleted_post_ids)) & 
                (~df_existing['Parent ID'].isin(deleted_post_ids))
            ]
            # Update existing data with new likes/comments
            for idx, row in df_new.iterrows():
                mask = df_existing['ID'] == row['ID']
                if mask.any():
                    df_existing.loc[mask, 'Likes'] = row['Likes']
                    df_existing.loc[mask, 'Comment Count'] = row['Comment Count']
                    df_existing.loc[mask, 'Time'] = row['Time']
            df_combined = pd.concat([df_new, df_existing], ignore_index=True)
            df_combined = df_combined.drop_duplicates(subset=['ID'], keep='first')
            df_combined = df_combined.sort_values('Time', ascending=False, na_position='last')
            # Filter again to ensure no deleted posts or comments
            df_combined = df_combined[
                (~df_combined['ID'].isin(deleted_post_ids)) & 
                (~df_combined['Parent ID'].isin(deleted_post_ids))
            ]
        else:
            df_combined = df_new.sort_values('Time', ascending=False, na_position='last')

        df_combined['Time'] = df_combined['Time'].apply(
            lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if pd.notna(x) else ''
        )

        with pd.ExcelWriter(self.excel_file, engine='openpyxl', mode='w') as writer:
            df_combined.to_excel(writer, sheet_name='Facebook Data', index=False)
            workbook = writer.book
            worksheet = workbook['Facebook Data']
            column_widths = {
                'A': 10, 'B': 20, 'C': 15, 'D': 20, 'E': 20, 'F': 80,
                'G': 40, 'H': 20, 'I': 30, 'J': 10, 'K': 15
            }
            for col_letter, width in column_widths.items():
                worksheet.column_dimensions[col_letter].width = width
                for cell in worksheet[col_letter][1:]:
                    if col_letter in ['F', 'I']:
                        cell.alignment = Alignment(wrapText=True, vertical='top', horizontal='left')
                        cell.font = Font(name='Calibri', size=11)
                    else:
                        cell.alignment = Alignment(wrapText=False, vertical='top', horizontal='left')
                        cell.font = Font(name='Calibri', size=11)
            for cell in worksheet[1]:
                cell.alignment = Alignment(wrapText=False, vertical='center', horizontal='center')
                cell.font = Font(name='Calibri', size=11, bold=True)
            for row_idx in range(2, worksheet.max_row + 1):
                content_cell = worksheet.cell(row=row_idx, column=6)
                parent_content_cell = worksheet.cell(row=row_idx, column=9)
                max_height = 15
                for cell in [content_cell, parent_content_cell]:
                    if cell.value:
                        char_count = len(str(cell.value))
                        chars_per_line = 70 if cell.column == 6 else 40
                        lines = max(1, char_count // chars_per_line + (1 if char_count % chars_per_line else 0))
                        height = lines * 15
                        max_height = max(max_height, height)
                worksheet.row_dimensions[row_idx].height = min(max_height, 800)
        logger.info(f"Excel file updated at {self.excel_file}")