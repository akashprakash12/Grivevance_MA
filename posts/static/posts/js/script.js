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
