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