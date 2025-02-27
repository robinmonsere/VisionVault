from flask import Flask, render_template, send_from_directory, jsonify, abort
import os
import litellm  # For Grok API integration (install with `pip install litellm`)

app = Flask(__name__)

# Root folder to scan (updated to your path)
ROOT_FOLDER = r"C:\Users\monse\Pictures\X"

# Configure LiteLLM with your Grok API key
litellm.api_key = "your_grok_api_key_here"  # Replace with your actual Grok API key from xAI
litellm.api_base = "https://api.grok.xai"  # Adjust based on xAI's API endpoint (check docs)

def process_image(file_path):
    """Process an image with Grok API and return general descriptive tags."""
    try:
        with open(file_path, 'rb') as f:
            # Use LiteLLM to call Grok's vision model for general image description
            response = litellm.completion(
                model="grok/grok-2-vision-1212",  # Use Grok's vision model
                messages=[{"role": "user", "content": "Describe this image and provide 3-5 general descriptive tags (e.g., cat, beach, sunset)."}],
                files=[{"file": f, "type": "image/*"}]  # Accepts jpg, jpeg, png, webp
            )
            # Extract tags from the response (assuming Grok returns a comma-separated string or list)
            description = response.choices[0].message.content
            # Parse tags (simple split on commas or extract from description)
            tags = [tag.strip().lower() for tag in description.split(',')[:5]]  # Limit to 5 tags
            if not tags or tags == ['']:
                tags = ["Pending tags"]  # Fallback if no tags are returned
            return tags
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")
        return ["Pending tags"]

def update_tags(folder_path):
    """Scan a folder, process image files, and update tags.txt."""
    full_path = os.path.join(ROOT_FOLDER, folder_path) if folder_path else ROOT_FOLDER
    tags_data = {}
    if not os.path.exists(full_path):
        return
    try:
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path):
                file_extension = os.path.splitext(item)[1].lower()
                if file_extension in ('.jpg', '.jpeg', '.png', '.webp'):
                    tags = process_image(item_path)
                    tags_data[item] = ", ".join(tags)
        # Write to tags.txt in the folder
        tags_file = os.path.join(full_path, 'tags.txt')
        with open(tags_file, 'w', encoding='utf-8') as f:
            for filename, tags in tags_data.items():
                f.write(f"{filename}: {tags}\n")
    except Exception as e:
        print(f"Error updating tags for {full_path}: {e}")

def get_folder_tree(path, base_path=""):
    """Build a nested dictionary of folders with full relative paths, excluding root."""
    tree = []
    if not os.path.exists(path):
        return [{"name": "No folders found", "path": "", "subfolders": []}]
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            rel_path = os.path.join(base_path, item) if base_path else item
            if os.path.isdir(item_path):
                folder = {
                    "name": item,
                    "path": rel_path,
                    "subfolders": get_folder_tree(item_path, rel_path)
                }
                tree.append(folder)
    except Exception as e:
        print(f"Error scanning folder {path}: {e}")
        return [{"name": f"Error: {str(e)}", "path": "", "subfolders": []}]
    return tree

def get_files_in_folder(path):
    """Get list of all files and subfolders in a folder."""
    items = []
    if not path or not os.path.exists(os.path.join(ROOT_FOLDER, path)):
        return items  # Return empty if path doesn't exist or isn't specified
    try:
        effective_path = os.path.join(ROOT_FOLDER, path)
        for item in os.listdir(effective_path):
            item_path = os.path.join(effective_path, item)
            rel_path = os.path.relpath(item_path, ROOT_FOLDER).replace("\\", "/")  # Normalize to forward slashes
            if os.path.isdir(item_path):
                items.append({
                    "name": item,
                    "path": rel_path,
                    "type": "folder",
                    "tags": ""
                })
            elif os.path.isfile(item_path):
                file_extension = os.path.splitext(item)[1].lower() or "unknown"
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                # Read tags from tags.txt if it exists
                tags = "Pending tags"
                tags_file = os.path.join(effective_path, 'tags.txt')
                if os.path.exists(tags_file):
                    with open(tags_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.startswith(item + ':'):
                                tags = line.split(':', 1)[1].strip()
                                break
                items.append({
                    "name": item,  # Keep full name, let CSS handle wrapping
                    "path": rel_path,
                    "type": file_type,
                    "tags": tags
                })
        # Sort: folders first, then files
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
    except Exception as e:
        print(f"Error listing items in {effective_path}: {e}")
        return [{"name": f"Error: {str(e)}", "type": "error", "path": "", "tags": ""}]
    return items

# Serve the main page with folder tree
@app.route('/')
def index():
    folder_tree = get_folder_tree(ROOT_FOLDER)
    return render_template('index.html', folder_tree=folder_tree)

# Serve static files (CSS, JS)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

# Serve actual image files
@app.route('/files/<path:file_path>')
def serve_file(file_path):
    full_path = os.path.join(ROOT_FOLDER, file_path)
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(ROOT_FOLDER, file_path, as_attachment=False)

# API endpoint to fetch folder tree
@app.route('/api/folder-tree')
def api_folder_tree():
    folder_tree = get_folder_tree(ROOT_FOLDER)
    return jsonify(folder_tree)

# API endpoint to fetch files and folders in a folder with path components for breadcrumbs
@app.route('/api/files/<path:folder_path>')
def api_files(folder_path):
    try:
        items = get_files_in_folder(folder_path)
        # Generate breadcrumbs if folder_path exists
        breadcrumbs = []
        if folder_path:
            current_path = ""
            for part in folder_path.split('/'):
                if part:
                    current_path = os.path.join(current_path, part) if current_path else part
                    breadcrumbs.append({
                        "name": part,
                        "path": current_path
                    })
        return jsonify({
            "items": items,
            "breadcrumbs": breadcrumbs if breadcrumbs else None
        })
    except Exception as e:
        print(f"API error for folder_path {folder_path}: {e}")
        return jsonify({"error": str(e)}), 500

# Trigger tag update on demand (e.g., for a specific folder)
@app.route('/api/update-tags/<path:folder_path>', methods=['POST'])
def update_folder_tags(folder_path):
    try:
        update_tags(folder_path)
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error updating tags for {folder_path}: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Optionally, update tags for all folders on startup (only images for now)
    for root, dirs, files in os.walk(ROOT_FOLDER):
        rel_root = os.path.relpath(root, ROOT_FOLDER)
        update_tags(rel_root)
    app.run(host='127.0.0.1', port=5000, debug=True)