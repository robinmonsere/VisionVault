from flask import Flask, render_template, send_from_directory, jsonify, abort, request
import os
import litellm  # For Grok API integration
from datetime import datetime
from dotenv import load_dotenv  # Load environment variables from .env
import base64  # For encoding image files
import win32file  # For setting/checking hidden attribute on Windows
import win32con  # For Windows file attributes

app = Flask(__name__)

# Load environment variables from .env file explicitly
load_dotenv('.env')

# Root folder to scan (updated to your path)
ROOT_FOLDER = r"C:\Users\monse\Pictures\X"

# Set Grok API key from environment variable
litellm.api_key = os.environ.get('XAI_API_KEY')
litellm.api_base = "https://api.grok.xai"  # Adjust based on xAI's API endpoint (check docs)


def is_hidden(filepath):
    """Check if a file is hidden on Windows."""
    try:
        attrs = win32file.GetFileAttributes(filepath)
        return bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        return filepath.startswith('.')


def process_image(file_path):
    """Process an image with Grok API and return general descriptive tags and description."""
    try:
        # Read and encode the image as base64 to avoid BufferedReader issues
        with open(file_path, 'rb') as f:
            # Encode the image in base64
            encoded_image = base64.b64encode(f.read()).decode('utf-8')

        # Use LiteLLM to call Grok's vision model with base64-encoded image
        response = litellm.completion(
            model="xai/grok-2-vision-1212",  # Use xAI's vision model (verified with LiteLLM provider list)
            messages=[{"role": "user", "content": [
                {"type": "text",
                 "text": "Describe this image and provide 3-5 general descriptive tags (e.g., cat, beach, sunset)."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}  # Use base64 URL
            ]}],
        )
        # Extract tags and description from the response
        description = response.choices[0].message.content
        # Parse tags (simple split on commas or extract from description)
        tags = [tag.strip().lower() for tag in description.split(',')[:5]]  # Limit to 5 tags
        if not tags or tags == ['']:
            tags = ["Pending tags"]  # Fallback if no tags are returned
        return tags, description
    except Exception as e:
        print(f"Error processing image {file_path}: {e}")
        return ["Pending tags"], "Error processing image"


def update_tags(folder_path):
    """Scan a folder, process only untagged files, and update .tags.txt (hidden file)."""
    full_path = os.path.join(ROOT_FOLDER, folder_path) if folder_path else ROOT_FOLDER
    if not os.path.exists(full_path):
        return
    tags_data = {}
    tags_file = os.path.join(full_path, '.tags.txt')  # Use hidden file name (.tags.txt)
    existing_tags = {}
    # Load existing tags if .tags.txt exists
    if os.path.exists(tags_file):
        try:
            with open(tags_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        parts = line.strip().split(':', 3)  # Split into name, format, tags, description
                        if len(parts) == 4:
                            filename, file_format, tags, desc = parts
                            existing_tags[filename] = {
                                "format": file_format,
                                "tags": tags,
                                "description": desc
                            }
        except PermissionError as e:
            print(f"Permission denied reading {tags_file}: {e}")
            return
        except Exception as e:
            print(f"Error reading tags for {full_path}: {e}")
            return

    try:
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path) and not is_hidden(item_path):
                file_extension = os.path.splitext(item)[1].lower() or "unknown"
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                # Check if file already has tags or needs processing
                if item not in existing_tags or existing_tags[item]["tags"] == "Pending tags":
                    if file_type == "image":
                        tags, description = process_image(item_path)
                    else:
                        tags = ["Pending tags"]
                        description = "No description available"
                    tags_data[item] = {
                        "format": file_type,
                        "tags": ", ".join(tags),
                        "description": description
                    }
                else:
                    tags_data[item] = existing_tags[item]  # Use existing tags and description
        # Write or update .tags.txt in the folder and hide it on Windows
        if tags_data:
            try:
                with open(tags_file, 'w', encoding='utf-8') as f:
                    for filename, data in tags_data.items():
                        f.write(f"{filename}:{data['format']}:{data['tags']}:{data['description']}\n")
                # Set the file as hidden on Windows
                try:
                    win32file.SetFileAttributes(tags_file, win32con.FILE_ATTRIBUTE_HIDDEN)
                except Exception as e:
                    print(f"Warning: Could not set hidden attribute for {tags_file}: {e}")
            except PermissionError as e:
                print(f"Permission denied writing to {tags_file}: {e}")
                return
            except Exception as e:
                print(f"Error writing tags for {full_path}: {e}")
                return
    except Exception as e:
        print(f"Error updating tags for {full_path}: {e}")


def initialize_tags():
    """Scan all folders and files, ensuring every non-hidden file is listed in .tags.txt with 'untagged' status, without AI processing."""
    for root, dirs, files in os.walk(ROOT_FOLDER):
        rel_root = os.path.relpath(root, ROOT_FOLDER)
        full_path = os.path.join(ROOT_FOLDER, rel_root)
        tags_file = os.path.join(full_path, '.tags.txt')
        existing_tags = {}
        # Load existing tags if .tags.txt exists
        if os.path.exists(tags_file):
            try:
                with open(tags_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            parts = line.strip().split(':', 3)
                            if len(parts) == 4:
                                filename, file_format, tags, desc = parts
                                existing_tags[filename] = {
                                    "format": file_format,
                                    "tags": tags,
                                    "description": desc
                                }
            except PermissionError as e:
                print(f"Permission denied reading {tags_file}: {e}")
                continue
            except Exception as e:
                print(f"Error reading tags for {full_path}: {e}")
                continue

        tags_data = existing_tags.copy()
        try:
            for item in files:
                item_path = os.path.join(full_path, item)
                if os.path.isfile(item_path) and not is_hidden(item_path):
                    file_extension = os.path.splitext(item)[1].lower() or "unknown"
                    file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                    if item not in tags_data:
                        tags_data[item] = {
                            "format": file_type,
                            "tags": "untagged",  # Default status for new files, no AI processing
                            "description": "No description available"
                        }
            # Write or update .tags.txt in the folder and hide it on Windows
            if tags_data:
                try:
                    with open(tags_file, 'w', encoding='utf-8') as f:
                        for filename, data in tags_data.items():
                            f.write(f"{filename}:{data['format']}:{data['tags']}:{data['description']}\n")
                    # Set the file as hidden on Windows
                    try:
                        win32file.SetFileAttributes(tags_file, win32con.FILE_ATTRIBUTE_HIDDEN)
                    except Exception as e:
                        print(f"Warning: Could not set hidden attribute for {tags_file}: {e}")
                except PermissionError as e:
                    print(f"Permission denied writing to {tags_file}: {e}")
                    continue
                except Exception as e:
                    print(f"Error writing tags for {full_path}: {e}")
                    continue
        except Exception as e:
            print(f"Error initializing tags for {full_path}: {e}")


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
    """Get list of all non-hidden files and subfolders in a folder."""
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
            elif os.path.isfile(item_path) and not is_hidden(item_path):
                file_extension = os.path.splitext(item)[1].lower() or "unknown"
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                # Read tags from .tags.txt if it exists
                tags = "untagged"  # Default to "untagged" for consistency
                description = "No description available"
                tags_file = os.path.join(effective_path, '.tags.txt')
                if os.path.exists(tags_file):
                    try:
                        with open(tags_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.startswith(item + ':'):
                                    parts = line.strip().split(':', 3)
                                    if len(parts) == 4:
                                        _, file_format, tag_string, desc = parts
                                        tags = tag_string
                                        description = desc
                                    break
                    except PermissionError as e:
                        print(f"Permission denied reading {tags_file}: {e}")
                        tags = "untagged"
                        description = "Permission error"
                    except Exception as e:
                        print(f"Error reading tags for {item_path}: {e}")
                        tags = "untagged"
                        description = "Error reading tags"
                items.append({
                    "name": item,  # Keep full name, let CSS handle wrapping
                    "path": rel_path,
                    "type": file_type,
                    "tags": tags,
                    "description": description  # Add description to items for future use
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


# Update file details (name, tags, description) in .tags.txt
@app.route('/api/update-file/<path:file_path>', methods=['POST'])
def update_file(file_path):
    try:
        data = request.get_json()
        new_name = data.get('name')
        new_tags = data.get('tags', 'untagged')
        new_description = data.get('description', 'No description available')

        # Parse the folder path and current filename from file_path
        folder_path = os.path.dirname(file_path) if file_path else ""
        current_name = os.path.basename(file_path)

        full_path = os.path.join(ROOT_FOLDER, folder_path)
        tags_file = os.path.join(full_path, '.tags.txt')

        if not os.path.exists(full_path) or not os.path.isfile(os.path.join(full_path, current_name)):
            return jsonify({"error": "File not found"}), 404

        existing_tags = {}
        updated = False
        if os.path.exists(tags_file):
            try:
                with open(tags_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            parts = line.strip().split(':', 3)
                            if len(parts) == 4:
                                filename, file_format, tags, desc = parts
                                existing_tags[filename] = {
                                    "format": file_format,
                                    "tags": tags,
                                    "description": desc
                                }
            except PermissionError as e:
                print(f"Permission denied reading {tags_file}: {e}")
                return jsonify({"error": f"Permission denied: {str(e)}"}), 500
            except Exception as e:
                print(f"Error reading tags for {tags_file}: {e}")
                return jsonify({"error": str(e)}), 500

        # Get current file details
        file_extension = os.path.splitext(current_name)[1].lower() or "unknown"
        file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]

        # Update or add the file entry
        if current_name in existing_tags:
            existing_tags[current_name] = {
                "format": file_type,
                "tags": new_tags if new_tags != "untagged" else existing_tags[current_name]["tags"],
                "description": new_description
            }
            updated = True

        # If renaming, handle the file rename on disk and update tags.txt
        if new_name and new_name != current_name:
            new_full_path = os.path.join(full_path, new_name)
            if not os.path.exists(new_full_path):  # Only rename if new name doesn't exist
                try:
                    os.rename(os.path.join(full_path, current_name), new_full_path)
                    if current_name in existing_tags:
                        existing_tags[new_name] = existing_tags.pop(current_name)
                        existing_tags[new_name]["format"] = file_type
                        existing_tags[new_name]["tags"] = new_tags if new_tags != "untagged" else \
                        existing_tags[new_name]["tags"]
                        existing_tags[new_name]["description"] = new_description
                        updated = True
                except PermissionError as e:
                    print(f"Permission denied renaming {current_name} to {new_name}: {e}")
                    return jsonify({"error": f"Permission denied: {str(e)}"}), 500
                except Exception as e:
                    print(f"Error renaming file {current_name}: {e}")
                    return jsonify({"error": str(e)}), 500

        # Write updated tags to .tags.txt
        if updated and existing_tags:
            try:
                with open(tags_file, 'w', encoding='utf-8') as f:
                    for filename, data in existing_tags.items():
                        f.write(f"{filename}:{data['format']}:{data['tags']}:{data['description']}\n")
                # Ensure .tags.txt remains hidden
                try:
                    win32file.SetFileAttributes(tags_file, win32con.FILE_ATTRIBUTE_HIDDEN)
                except Exception as e:
                    print(f"Warning: Could not set hidden attribute for {tags_file}: {e}")
            except PermissionError as e:
                print(f"Permission denied writing to {tags_file}: {e}")
                return jsonify({"error": f"Permission denied: {str(e)}"}), 500
            except Exception as e:
                print(f"Error writing tags for {tags_file}: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify(
            {"status": "success", "new_path": os.path.join(folder_path, new_name) if new_name else file_path})
    except Exception as e:
        print(f"Error updating file {file_path}: {e}")
        return jsonify({"error": str(e)}), 500


# Delete file and update .tags.txt
@app.route('/api/delete-file/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    try:
        # Parse the folder path and filename from file_path
        folder_path = os.path.dirname(file_path) if file_path else ""
        current_name = os.path.basename(file_path)

        full_path = os.path.join(ROOT_FOLDER, folder_path)
        file_full_path = os.path.join(full_path, current_name)
        tags_file = os.path.join(full_path, '.tags.txt')

        if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
            return jsonify({"error": "File not found"}), 404

        # Delete the file from disk
        try:
            os.remove(file_full_path)
            print(f"Successfully deleted file: {file_full_path}")
        except PermissionError as e:
            print(f"Permission warning for deleting {file_full_path}, but file may still be deleted: {e}")
            # Check if the file was actually deleted despite the permission error
            if not os.path.exists(file_full_path):
                print(f"File {file_full_path} was deleted despite permission warning.")
            else:
                return jsonify({"error": f"Permission denied: {str(e)}"}), 500
        except Exception as e:
            print(f"Error deleting file {file_full_path}: {e}")
            return jsonify({"error": str(e)}), 500

        # Update .tags.txt by removing the file entry
        if os.path.exists(tags_file):
            try:
                existing_tags = {}
                with open(tags_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            parts = line.strip().split(':', 3)
                            if len(parts) == 4 and parts[0] != current_name:
                                filename, file_format, tags, desc = parts
                                existing_tags[filename] = {
                                    "format": file_format,
                                    "tags": tags,
                                    "description": desc
                                }

                if existing_tags:
                    with open(tags_file, 'w', encoding='utf-8') as f:
                        for filename, data in existing_tags.items():
                            f.write(f"{filename}:{data['format']}:{data['tags']}:{data['description']}\n")
                    # Ensure .tags.txt remains hidden
                    try:
                        win32file.SetFileAttributes(tags_file, win32con.FILE_ATTRIBUTE_HIDDEN)
                    except Exception as e:
                        print(f"Warning: Could not set hidden attribute for {tags_file}: {e}")
                else:
                    # If no entries remain, delete .tags.txt
                    try:
                        os.remove(tags_file)
                        try:
                            win32file.SetFileAttributes(tags_file,
                                                        win32con.FILE_ATTRIBUTE_HIDDEN)  # Ensure it’s marked as hidden if deletion fails
                        except Exception as e:
                            print(f"Warning: Could not set hidden attribute after deleting {tags_file}: {e}")
                    except Exception as e:
                        print(f"Error deleting empty {tags_file}: {e}")
            except PermissionError as e:
                print(f"Permission denied updating {tags_file}: {e}")
                return jsonify({"error": f"Permission denied: {str(e)}"}), 500
            except Exception as e:
                print(f"Error updating tags for {tags_file}: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run on startup: initialize tags for all non-hidden files, setting new files to "untagged" without AI processing
    initialize_tags()
    app.run(host='127.0.0.1', port=5000, debug=True)