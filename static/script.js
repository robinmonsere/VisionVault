// Placeholder for search functionality
function searchFiles() {
    const query = document.getElementById('search-input').value;
    alert(`Searching VisionVault for: ${query}`);
    // Later: Send query to backend for AI processing
}

// Folder tree interaction
document.querySelectorAll('.folder-tree li').forEach(item => {
    item.addEventListener('click', () => {
        const folderPath = item.getAttribute('data-path');
        fetchFiles(folderPath);
    });
});

// Fetch and display files in the selected folder
function fetchFiles(folderPath) {
    fetch(`/api/files/${encodeURIComponent(folderPath)}`)
        .then(response => response.json())
        .then(files => {
            const fileGrid = document.getElementById('file-grid');
            fileGrid.innerHTML = ''; // Clear current files
            if (files.length === 0) {
                fileGrid.innerHTML = '<p>No files found in this folder.</p>';
                return;
            }
            files.forEach(file => {
                const fileCard = document.createElement('div');
                fileCard.className = 'file-card';
                if (file.type === 'image') {
                    fileCard.innerHTML = `
                        <img src="/static/placeholder.jpg" alt="${file.name}">
                        <p>${file.name}</p>
                        <span class="tags">${file.tags}</span>
                    `;
                } else {
                    fileCard.innerHTML = `
                        <div class="file-icon">${file.type.toUpperCase()}</div>
                        <p>${file.name}</p>
                        <span class="tags">${file.tags}</span>
                    `;
                }
                fileGrid.appendChild(fileCard);
            });
        })
        .catch(error => {
            console.error('Error fetching files:', error);
            document.getElementById('file-grid').innerHTML = '<p>Error loading files.</p>';
        });
}

// Handle image paste anywhere on the page
document.addEventListener('paste', (event) => {
    const items = (event.clipboardData || event.originalEvent.clipboardData).items;
    for (let item of items) {
        if (item.type.indexOf('image') !== -1) {
            const blob = item.getAsFile();
            savePastedImage(blob);
            event.preventDefault();
        }
    }
});

function savePastedImage(blob) {
    if (blob) {
        alert('Saving pasted SpaceX image to VisionVault');
        // Later: Send blob to backend for processing and storage
    }
}