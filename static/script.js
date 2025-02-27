// Placeholder for search functionality
function searchFiles() {
    const query = document.getElementById('search-input').value;
    alert(`Searching VisionVault for: ${query}`);
    // Later: Send query to backend for AI processing
}

// Folder tree interaction
document.querySelectorAll('.folder-tree li').forEach(item => {
    item.addEventListener('click', (event) => {
        // Prevent bubbling up to parent folders
        event.stopPropagation();
        const folderPath = item.getAttribute('data-path');
        if (folderPath) {
            fetchFiles(folderPath.trim().replace('\\', '/')); // Ensure forward slashes
        }
    });
});

// Fetch and display files, folders, and breadcrumbs in the selected folder
function fetchFiles(folderPath) {
    if (!folderPath) {
        const fileGrid = document.getElementById('file-grid');
        fileGrid.innerHTML = '<p>No folder selected. Click a folder to view its contents.</p>';
        document.getElementById('breadcrumbs').innerHTML = ''; // Clear breadcrumbs
        return;
    }
    // Normalize path to use forward slashes
    folderPath = folderPath.replace('\\', '/');
    fetch(`/api/files/${encodeURIComponent(folderPath)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            const { items, breadcrumbs } = data;
            const fileGrid = document.getElementById('file-grid');
            const breadcrumbsDiv = document.getElementById('breadcrumbs');
            fileGrid.innerHTML = ''; // Clear current items
            breadcrumbsDiv.innerHTML = ''; // Clear breadcrumbs

            // Render breadcrumbs if available
            if (breadcrumbs) {
                const breadcrumbList = document.createElement('nav');
                breadcrumbList.className = 'breadcrumb-nav';
                const parts = breadcrumbs.map((crumb, index) => {
                    const span = document.createElement('span');
                    span.textContent = crumb.name;
                    if (index < breadcrumbs.length - 1) {
                        span.textContent += ' > ';
                    }
                    if (index < breadcrumbs.length - 1) {
                        span.className = 'breadcrumb clickable';
                        span.addEventListener('click', () => fetchFiles(crumb.path.trim().replace('\\', '/'))); // Normalize path here
                    } else {
                        span.className = 'breadcrumb current'; // Highlight current folder in white
                    }
                    return span;
                });
                parts.forEach(part => breadcrumbList.appendChild(part));
                breadcrumbsDiv.appendChild(breadcrumbList);
            }

            // Render files and folders
            if (data.error) {
                fileGrid.innerHTML = `<p>Error: ${data.error}</p>`;
                return;
            }
            if (items.length === 0 || (items.length === 1 && items[0].type === "error")) {
                fileGrid.innerHTML = '<p>No items found in this folder.</p>';
                return;
            }
            items.forEach(item => {
                const fileCard = document.createElement('div');
                fileCard.className = 'file-card';
                if (item.type === 'folder') {
                    fileCard.innerHTML = `
                        <div class="file-icon">FOLDER</div>
                        <p>${item.name}</p>
                        <span class="tags"></span>
                    `;
                    fileCard.addEventListener('click', () => fetchFiles(item.path.trim().replace('\\', '/')));
                } else if (item.type === 'image') {
                    fileCard.innerHTML = `
                        <img src="/files/${encodeURIComponent(item.path)}" alt="${item.name}" onerror="this.src='/static/placeholder.jpg'">
                        <p>${item.name}</p>
                        <span class="tags">${item.tags}</span>
                    `;
                } else {
                    fileCard.innerHTML = `
                        <div class="file-icon">${item.type.toUpperCase()}</div>
                        <p>${item.name}</p>
                        <span class="tags">${item.tags}</span>
                    `;
                }
                fileGrid.appendChild(fileCard);
            });
        })
        .catch(error => {
            console.error('Error fetching items:', error);
            document.getElementById('file-grid').innerHTML = '<p>Error loading items.</p>';
            document.getElementById('breadcrumbs').innerHTML = ''; // Clear breadcrumbs on error
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