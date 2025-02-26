from flask import Flask, render_template, send_from_directory, jsonify
import os

app = Flask(__name__)

# Root folder to scan (change this to your preferred path)
ROOT_FOLDER = r"C:\Users\monse\Pictures\X"

def get_folder_tree(path):
    """Build a nested dictionary of folders."""
    tree = []
    if not os.path.exists(path):
        return [{"name": "No folders found", "subfolders": []}]
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                folder = {
                    "name": item,
                    "subfolders": get_folder_tree(item_path)
                }
                tree.append(folder)
    except Exception as e:
        print(f"Error scanning folder {path}: {e}")
        return [{"name": f"Error: {str(e)}", "subfolders": []}]
    return tree

def get_files_in_folder(path):
    """Get list of files in a folder with basic info."""
    files = []
    if not os.path.exists(path):
        return files
    try:
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isfile(item_path) and item.lower().endswith(('.jpg', '.jpeg', '.png')):  # Images only for now
                files.append({
                    "name": item,
                    "path": item_path,
                    "tags": "Pending tags"  # Placeholder until Grok API integration
                })
    except Exception as e:
        print(f"Error listing files in {path}: {e}")
    return files

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

# API endpoint to fetch files in a folder
@app.route('/api/files/<path:folder_path>')
def api_files(folder_path):
    full_path = os.path.join(ROOT_FOLDER, folder_path)
    files = get_files_in_folder(full_path)
    return jsonify(files)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)