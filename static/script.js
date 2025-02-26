// Placeholder for search functionality
function searchFiles() {
    const query = document.getElementById('search-input').value;
    alert(`Searching VisionVault for: ${query}`);
    // Later: Send query to backend for AI processing
}

// Placeholder for folder tree interaction
document.querySelectorAll('.folder-tree li').forEach(item => {
    item.addEventListener('click', () => {
        alert(`Exploring VisionVault folder: ${item.textContent.trim()}`);
        // Later: Load files for this folder
    });
});

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