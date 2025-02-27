// Placeholder for search functionality
function searchFiles() {
    const query = document.getElementById('search-input').value;
    if (!query.trim()) {
        alert('Please enter a search query.');
        return;
    }
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(results => {
            const fileGrid = document.getElementById('file-grid');
            const breadcrumbsDiv = document.getElementById('breadcrumbs');
            fileGrid.innerHTML = ''; // Clear current items
            breadcrumbsDiv.innerHTML = '<nav class="breadcrumb-nav">Search Results</nav>'; // Simple breadcrumb for search

            if (results.error) {
                fileGrid.innerHTML = `<p>Error: ${results.error}</p>`;
                return;
            }
            if (results.length === 0) {
                fileGrid.innerHTML = '<p>No results found.</p>';
                return;
            }
            results.forEach(item => {
                const fileCard = document.createElement('div');
                fileCard.className = 'file-card';
                const fileExtension = os.path.splitext(item.path)[1].lower() or "unknown"
                file_type = "image" if fileExtension in ('.jpg', '.jpeg', '.png', '.webp') else fileExtension[1:]
                if (file_type === 'image') {
                    fileCard.innerHTML = `
                        <img src="/files/${encodeURIComponent(item.path)}" alt="${item.name}" onerror="this.src='/static/placeholder.jpg'">
                        <p>${item.name}</p>
                        <span class="tags">${item.tags}</span>
                    `;
                } else {
                    fileCard.innerHTML = `
                        <div class="file-icon">${file_type.toUpperCase()}</div>
                        <p>${item.name}</p>
                        <span class="tags">${item.tags}</span>
                    `;
                }
                fileCard.addEventListener('click', () => {
                    showFileEditModal(item.path, item.name, item.tags, item.description || "No description available");
                });
                fileGrid.appendChild(fileCard);
            });
        })
        .catch(error => {
            console.error('Error searching files:', error);
            document.getElementById('file-grid').innerHTML = '<p>Error searching files.</p>';
            document.getElementById('breadcrumbs').innerHTML = ''; // Clear breadcrumbs on error
        });
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
                        span.addEventListener('click', () => fetchFiles(crumb.path.trim().replace('\\', '/')));
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
                } else {
                    fileCard.innerHTML = `
                        ${item.type === 'image' ? `<img src="/files/${encodeURIComponent(item.path)}" alt="${item.name}" onerror="this.src='/static/placeholder.jpg'">` : `<div class="file-icon">${item.type.toUpperCase()}</div>`}
                        <p>${item.name}</p>
                        <span class="tags">${item.tags}</span>
                    `;
                    fileCard.addEventListener('click', () => {
                        showFileEditModal(item.path, item.name, item.tags, item.description || "No description available");
                    });
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
        const currentPath = document.querySelector('.breadcrumb.current')?.parentElement.textContent.split(' > ').slice(0, -1).join('/').trim().replace('\\', '/');
        if (currentPath) {
            const formData = new FormData();
            formData.append('file', blob);
            fetch(`/api/update-tags/${encodeURIComponent(currentPath)}`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(`Error saving image: ${data.error}`);
                } else {
                    alert('Image saved and tagged successfully!');
                    fetchFiles(currentPath); // Refresh the current folder
                }
            })
            .catch(error => {
                console.error('Error saving image:', error);
                alert('Error saving image.');
            });
        } else {
            alert('No folder selected. Please select a folder before pasting.');
        }
    }
}

// Show file edit modal
function showFileEditModal(filePath, currentName, currentTags, currentDescription) {
    document.getElementById('file-name').value = currentName;
    document.getElementById('file-tags').value = currentTags === "untagged" ? "" : currentTags;
    document.getElementById('file-description').value = currentDescription;
    document.getElementById('file-edit-modal').style.display = 'block';

    document.getElementById('file-edit-form').onsubmit = async (e) => {
        e.preventDefault();
        const newName = document.getElementById('file-name').value.trim();
        const newTags = document.getElementById('file-tags').value.trim() || "untagged";
        const newDescription = document.getElementById('file-description').value.trim() || "No description available";

        try {
            const response = await fetch(`/api/update-file/${encodeURIComponent(filePath)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newName, tags: newTags, description: newDescription })
            });
            const data = await response.json();
            if (data.error) {
                alert(`Error updating file: ${data.error}`);
            } else {
                alert('File updated successfully!');
                closeModal();
                // Refresh the current folder
                const folderPath = filePath.split('/').slice(0, -1).join('/');
                fetchFiles(folderPath);
            }
        } catch (error) {
            console.error('Error updating file:', error);
            alert('Error updating file.');
        }
    };
}

// Close file edit modal
function closeModal() {
    document.getElementById('file-edit-modal').style.display = 'none';
    document.getElementById('file-edit-form').onsubmit = null; // Reset form submission
}