function updatePosts() {
       fetch('/comments-status/')
           .then(response => response.json())
           .then(data => {
               const postsList = document.getElementById('posts');
               postsList.innerHTML = '';
               for (let postId in data) {
                   const post = data[postId];
                   const li = document.createElement('li');
                   li.textContent = `Post ID: ${post.post_id} - ${post.reading ? 'Reading Comments' : 'Not Reading'}`;
                   postsList.appendChild(li);
               }
           });
   }

   setInterval(updatePosts, 30000); // Update every 30 seconds
   document.getElementById('postForm').addEventListener('submit', () => {
       setTimeout(updatePosts, 1000);
   });