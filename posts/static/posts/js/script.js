<<<<<<< HEAD
document.getElementById('postForm').addEventListener('submit', () => {
    console.log('Form submitted');
});
function updatePosts() {
    fetch('/facebook/comments-status/')
        .then(response => response.json())
        .then(data => {
            const postsList = document.getElementById('posts');
            postsList.innerHTML = '';
            if (Object.keys(data).length === 0) {
                postsList.innerHTML = '<p class="text-gray-500">No complaint posts found.</p>';
                return;
            }
            for (let postId in data) {
                const post = data[postId];
                const li = document.createElement('li');
                li.className = 'border-b pb-4';
                li.innerHTML = `
                    <div class="flex justify-between items-center">
                        <a href="https://www.facebook.com/${post.post_id}" target="_blank" class="text-blue-600 hover:underline">Post ID: ${post.post_id}</a>
                        <span class="text-gray-500 text-sm">${new Date(post.created_at).toLocaleString()}</span>
                    </div>
                    <p class="text-gray-700 mt-2">${post.message.substring(0, 100)}...</p>
                    ${post.comments.length ? `
                        <ul class="ml-6 mt-2 space-y-2">
                            ${post.comments.map(comment => `
                                <li class="text-gray-600 text-sm">
                                    <strong>${comment.author}:</strong> ${comment.message.substring(0, 50)}...
                                    <span class="text-gray-400 text-xs">(${new Date(comment.created_at).toLocaleString()})</span>
                                </li>
                            `).join('')}
                        </ul>
                    ` : '<p class="text-gray-500 text-sm mt-2">No comments yet.</p>'}
                `;
                postsList.appendChild(li);
            }
        })
        .catch(error => console.error('Error updating posts:', error));
}

setInterval(updatePosts, 30000); // Update every 30 seconds
document.getElementById('postForm').addEventListener('submit', () => {
    setTimeout(updatePosts, 1000);
});
updatePosts(); // Initial load
=======
document.getElementById('post-form')?.addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    const response = await fetch('{% url "posts:index" %}', {
        method: 'POST',
        body: formData,
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    });
    const result = await response.json();
    const postResult = document.getElementById('post-result');
    if (result.status === 'success') {
        postResult.innerHTML = `<div class="alert alert-success">Posted successfully! Post ID: ${result.post_id}</div>`;
        if (formData.get('read_comments') === 'on') {
            startCommentPolling(result.post_id);
        }
    } else {
        postResult.innerHTML = `<div class="alert alert-danger">Error: ${result.message}</div>`;
    }
});

function startCommentPolling(postId) {
    const commentsSection = document.getElementById('comments-section');
    if (!commentsSection) return;
    async function fetchComments() {
        const response = await fetch(`/posts/comments/${postId}/`);
        const result = await response.json();
        if (result.status === 'success') {
            let commentsHtml = `<h3>Comments for Post ${postId}</h3>`;
            commentsHtml += `<a href="/posts/download/${postId}/" class="btn btn-success mb-3">Download Comments as Excel</a>`;
            commentsHtml += '<ul id="comments-list" class="list-group">';
            if (result.comments.length > 0) {
                result.comments.forEach(comment => {
                    commentsHtml += `<li class="list-group-item">
                        <strong>${comment.name}</strong> at ${comment.created_time}: ${comment.message}
                    </li>`;
                });
            } else {
                commentsHtml += '<li class="list-group-item">No comments yet.</li>';
            }
            commentsHtml += '</ul>';
            commentsSection.innerHTML = commentsHtml;
        } else {
            commentsSection.innerHTML = `<div class="alert alert-warning">${result.message}</div>`;
            clearInterval(pollingInterval);
        }
    }
    fetchComments();
    const pollingInterval = setInterval(fetchComments, 10000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
>>>>>>> origin/thomas
