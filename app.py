from flask import Flask, render_template, send_from_directory, jsonify
import os

app = Flask(__name__)

# Root folder to scan (change this to your preferred path)
ROOT_FOLDER = r"C:\Users\monse\Pictures\X"

def get_folder_tree(path, base_path=""):
    """Build a nested dictionary of folders with full relative paths."""
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
    if not os.path.exists(path):
        return items
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
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
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png') else file_extension[1:]
                items.append({
                    "name": item,
                    "path": rel_path,
                    "type": file_type,
                    "tags": "Pending tags"
                })
        # Sort: folders first, then files
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
    except Exception as e:
        print(f"Error listing items in {path}: {e}")
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

# API endpoint to fetch folder tree
@app.route('/api/folder-tree')
def api_folder_tree():
    folder_tree = get_folder_tree(ROOT_FOLDER)
    return jsonify(folder_tree)

# API endpoint to fetch files and folders in a folder
@app.route('/api/files/<path:folder_path>')
def api_files(folder_path):
    full_path = os.path.join(ROOT_FOLDER, folder_path)
    items = get_files_in_folder(full_path)
    return jsonify(items)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)