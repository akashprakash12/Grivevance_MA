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