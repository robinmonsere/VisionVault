from flask import Flask, render_template, send_from_directory, jsonify, abort, request
import os
import litellm  # For Grok API integration
from datetime import datetime
from dotenv import load_dotenv  # Load environment variables from .env
import base64  # For encoding image files
import win32file  # For setting/checking hidden attribute on Windows
import win32con  # For Windows file attributes
import logging  # For detailed logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
    except Exception as e:
        logger.warning(f"Could not check hidden status for {filepath}: {e}")
        return filepath.startswith('.')


def get_file_attributes(filepath):
    """Get and log file attributes for diagnostics."""
    try:
        attrs = win32file.GetFileAttributes(filepath)
        is_hidden = bool(attrs & win32con.FILE_ATTRIBUTE_HIDDEN)
        is_readonly = bool(attrs & win32con.FILE_ATTRIBUTE_READONLY)
        logger.info(f"File attributes for {filepath}: Hidden={is_hidden}, Readonly={is_readonly}")
    except Exception as e:
        logger.error(f"Error getting attributes for {filepath}: {e}")


def toggle_hidden_file(filepath, hide=True):
    """Toggle the hidden attribute of a file."""
    try:
        if not os.path.exists(filepath):
            logger.error(f"File does not exist: {filepath}")
            return
        current_attrs = win32file.GetFileAttributes(filepath)
        if hide:
            # Add the hidden flag
            new_attrs = current_attrs | win32con.FILE_ATTRIBUTE_HIDDEN
        else:
            # Remove the hidden flag
            new_attrs = current_attrs & ~win32con.FILE_ATTRIBUTE_HIDDEN
        win32file.SetFileAttributes(filepath, new_attrs)
        logger.info(f"{'Hid' if hide else 'Unhid'} {filepath} successfully")
    except Exception as e:
        logger.error(f"Error toggling hidden attribute for {filepath}: {e}")


def process_image(file_path):
    """Process an image with Grok API and return general descriptive tags and description."""
    try:
        with open(file_path, 'rb') as f:
            encoded_image = base64.b64encode(f.read()).decode('utf-8')
        response = litellm.completion(
            model="xai/grok-2-vision-1212",
            messages=[{"role": "user", "content": [
                {"type": "text",
                 "text": "Describe this image and provide 3-5 general descriptive tags (e.g., cat, beach, sunset)."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
            ]}]
        )
        description = response.choices[0].message.content
        tags = [tag.strip().lower() for tag in description.split(',')[:5]] or ["Pending tags"]
        return tags, description
    except Exception as e:
        logger.error(f"Error processing image {file_path}: {e}")
        return ["Pending tags"], "Error processing image"


def read_tags_file(tags_file):
    """Read tags from a .tags.txt file and return a dictionary."""
    tags_data = {}
    if os.path.exists(tags_file):
        try:
            toggle_hidden_file(tags_file, hide=False)  # Unhide before reading
            with open(tags_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        parts = line.strip().split(':', 3)
                        if len(parts) == 4:
                            filename, file_format, tags, desc = parts
                            tags_data[filename] = {"format": file_format, "tags": tags, "description": desc}
            logger.info(f"Successfully read and closed {tags_file}")
            toggle_hidden_file(tags_file, hide=True)  # Re-hide after reading
        except PermissionError as e:
            logger.error(f"Permission denied reading {tags_file}: {e}")
        except Exception as e:
            logger.error(f"Error reading tags for {tags_file}: {e}")
    return tags_data


def write_tags_file(tags_file, tags_data):
    """Write tags to a .tags.txt file."""
    try:
        toggle_hidden_file(tags_file, hide=False)  # Unhide before writing
        with open(tags_file, 'w', encoding='utf-8') as f:
            for filename, data in tags_data.items():
                f.write(f"{filename}:{data['format']}:{data['tags']}:{data['description']}\n")
        get_file_attributes(tags_file)  # Log attributes after writing
        logger.info(f"Successfully wrote and closed {tags_file}")
        toggle_hidden_file(tags_file, hide=True)  # Re-hide after writing
    except PermissionError as e:
        logger.error(f"Permission denied writing to {tags_file}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error writing tags for {tags_file}: {e}")
        raise


def update_root_tags(root_tags_file, full_path, tags_data_entry, action="update"):
    """Update the root .tags.txt with a full path entry."""
    root_tags = read_tags_file(root_tags_file)
    if action == "update" or action == "add":
        root_tags[full_path] = tags_data_entry
    elif action == "delete":
        root_tags.pop(full_path, None)
    try:
        write_tags_file(root_tags_file, root_tags)
    except Exception as e:
        logger.warning(f"Root .tags.txt out of sync: {e}. Sync will be corrected on restart with initialize_tags()")
        raise


def update_tags(folder_path):
    """Scan a folder, process only untagged files, and update .tags.txt (hidden file)."""
    full_path = os.path.join(ROOT_FOLDER, folder_path) if folder_path else ROOT_FOLDER
    if not os.path.exists(full_path):
        return
    tags_data = {}
    tags_file = os.path.join(full_path, '.tags.txt')
    existing_tags = read_tags_file(tags_file)
    try:
        for item in os.listdir(full_path):
            item_path = os.path.join(full_path, item)
            if os.path.isfile(item_path) and not is_hidden(item_path):
                file_extension = os.path.splitext(item)[1].lower() or "unknown"
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                if item not in existing_tags or existing_tags[item]["tags"] == "Pending tags":
                    # Note: process_image() is not called here as per your request, to be handled later
                    tags = ["Pending tags"]  # Placeholder until process_image() is used
                    description = "No description available"  # Placeholder
                    tags_data[item] = {"format": file_type, "tags": ", ".join(tags), "description": description}
                else:
                    tags_data[item] = existing_tags[item]
        if tags_data:
            write_tags_file(tags_file, tags_data)
            rel_path = os.path.relpath(full_path, ROOT_FOLDER).replace("\\", "/")
            for item, data in tags_data.items():
                full_item_path = os.path.join(rel_path, item).replace("\\", "/")
                update_root_tags(os.path.join(ROOT_FOLDER, '.tags.txt'), full_item_path, data)
    except Exception as e:
        logger.error(f"Error updating tags for {full_path}: {e}")


def initialize_tags():
    """Scan all folders and files, ensuring every non-hidden file is listed in subfolder and root .tags.txt."""
    root_tags_file = os.path.join(ROOT_FOLDER, '.tags.txt')
    all_tags = {}
    for root, dirs, files in os.walk(ROOT_FOLDER):
        rel_root = os.path.relpath(root, ROOT_FOLDER)
        full_path_base = rel_root if rel_root != "." else ""
        tags_file = os.path.join(root, '.tags.txt')
        existing_tags = read_tags_file(tags_file)
        tags_data = existing_tags.copy()
        for item in files:
            item_path = os.path.join(root, item)
            if os.path.isfile(item_path) and not is_hidden(item_path):
                full_item_path = os.path.join(full_path_base, item).replace("\\", "/")
                file_extension = os.path.splitext(item)[1].lower() or "unknown"
                file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
                if item not in existing_tags or existing_tags[item]["tags"] == "Pending tags":
                    # Note: process_image() is not called here as per your request, to be handled later
                    tags = ["untagged"]  # Placeholder until process_image() is used
                    description = "No description available"  # Placeholder
                    tags_data[item] = {"format": file_type, "tags": ", ".join(tags), "description": description}
                    all_tags[full_item_path] = tags_data[item]
                else:
                    all_tags[full_item_path] = existing_tags[item]
        if tags_data:
            try:
                write_tags_file(tags_file, tags_data)
            except Exception as e:
                logger.error(f"Failed to update {tags_file}: {e}")
                continue
    # Write to root .tags.txt
    if all_tags:
        try:
            write_tags_file(root_tags_file, all_tags)
        except Exception as e:
            logger.error(f"Failed to initialize root .tags.txt: {e}")


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
        logger.error(f"Error scanning folder {path}: {e}")
        return [{"name": f"Error: {str(e)}", "path": "", "subfolders": []}]
    return tree


def get_files_in_folder(path):
    """Get list of all non-hidden files and subfolders in a folder."""
    items = []
    if not path or not os.path.exists(os.path.join(ROOT_FOLDER, path)):
        return items  # Return empty if path doesn't exist or isn't specified
    try:
        effective_path = os.path.join(ROOT_FOLDER, path)
        tags_file = os.path.join(effective_path, '.tags.txt')
        existing_tags = read_tags_file(tags_file)
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
                tags = existing_tags.get(item, {}).get("tags", "untagged")
                description = existing_tags.get(item, {}).get("description", "No description available")
                items.append({
                    "name": item,
                    "path": rel_path,
                    "type": file_type,
                    "tags": tags,
                    "description": description
                })
        items.sort(key=lambda x: (x["type"] != "folder", x["name"].lower()))
    except Exception as e:
        logger.error(f"Error listing items in {effective_path}: {e}")
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
        breadcrumbs = []
        if folder_path:
            current_path = ""
            for part in folder_path.split('/'):
                if part:
                    current_path = os.path.join(current_path, part) if current_path else part
                    breadcrumbs.append({"name": part, "path": current_path})
        return jsonify({"items": items, "breadcrumbs": breadcrumbs if breadcrumbs else None})
    except Exception as e:
        logger.error(f"API error for folder_path {folder_path}: {e}")
        return jsonify({"error": str(e)}), 500


# Trigger tag update on demand (e.g., for a specific folder)
@app.route('/api/update-tags/<path:folder_path>', methods=['POST'])
def update_folder_tags(folder_path):
    try:
        full_path = os.path.join(ROOT_FOLDER, folder_path) if folder_path else ROOT_FOLDER
        tags_file = os.path.join(full_path, '.tags.txt')
        root_tags_file = os.path.join(ROOT_FOLDER, '.tags.txt')
        update_tags(folder_path)
        rel_path = os.path.relpath(full_path, ROOT_FOLDER).replace("\\", "/")
        for item in os.listdir(full_path):
            if os.path.isfile(os.path.join(full_path, item)) and not is_hidden(os.path.join(full_path, item)):
                full_item_path = os.path.join(rel_path, item).replace("\\", "/")
                tags_data = read_tags_file(tags_file).get(item, {"format": "unknown", "tags": "untagged",
                                                                 "description": "No description available"})
                update_root_tags(root_tags_file, full_item_path, tags_data)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error updating tags for {folder_path}: {e}")
        return jsonify({"error": str(e)}), 500


# Update file details (name, tags, description) in .tags.txt
@app.route('/api/update-file/<path:file_path>', methods=['POST'])
def update_file(file_path):
    try:
        data = request.get_json()
        new_name = data.get('name')
        new_tags = data.get('tags', 'untagged')
        new_description = data.get('description', 'No description available')

        folder_path = os.path.dirname(file_path) if file_path else ""
        current_name = os.path.basename(file_path)

        full_path = os.path.join(ROOT_FOLDER, folder_path)
        tags_file = os.path.join(full_path, '.tags.txt')
        root_tags_file = os.path.join(ROOT_FOLDER, '.tags.txt')

        if not os.path.exists(full_path) or not os.path.isfile(os.path.join(full_path, current_name)):
            return jsonify({"error": "File not found"}), 404

        existing_tags = read_tags_file(tags_file)
        updated = False
        if current_name in existing_tags:
            file_extension = os.path.splitext(current_name)[1].lower() or "unknown"
            file_type = "image" if file_extension in ('.jpg', '.jpeg', '.png', '.webp') else file_extension[1:]
            existing_tags[current_name] = {
                "format": file_type,
                "tags": new_tags if new_tags != "untagged" else existing_tags[current_name]["tags"],
                "description": new_description
            }
            updated = True

        if new_name and new_name != current_name:
            new_full_path = os.path.join(full_path, new_name)
            if not os.path.exists(new_full_path):
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
                    logger.error(f"Permission denied renaming {current_name} to {new_name}: {e}")
                    return jsonify({"error": f"Permission denied: {str(e)}"}), 500
                except Exception as e:
                    logger.error(f"Error renaming file {current_name}: {e}")
                    return jsonify({"error": str(e)}), 500

        if updated:
            try:
                write_tags_file(tags_file, existing_tags)
                rel_path = os.path.relpath(full_path, ROOT_FOLDER).replace("\\", "/")
                full_item_path = os.path.join(rel_path, new_name if new_name else current_name).replace("\\", "/")
                update_root_tags(root_tags_file, full_item_path,
                                 existing_tags.get(new_name if new_name else current_name))
            except Exception as e:
                logger.error(f"Failed to update {tags_file} or root: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify(
            {"status": "success", "new_path": os.path.join(folder_path, new_name) if new_name else file_path})
    except Exception as e:
        logger.error(f"Error updating file {file_path}: {e}")
        return jsonify({"error": str(e)}), 500


# Delete file and update .tags.txt
@app.route('/api/delete-file/<path:file_path>', methods=['DELETE'])
def delete_file(file_path):
    try:
        folder_path = os.path.dirname(file_path) if file_path else ""
        current_name = os.path.basename(file_path)

        full_path = os.path.join(ROOT_FOLDER, folder_path)
        file_full_path = os.path.join(full_path, current_name)
        tags_file = os.path.join(full_path, '.tags.txt')
        root_tags_file = os.path.join(ROOT_FOLDER, '.tags.txt')

        if not os.path.exists(file_full_path) or not os.path.isfile(file_full_path):
            return jsonify({"error": "File not found"}), 404

        try:
            os.remove(file_full_path)
            logger.info(f"Successfully deleted file: {file_full_path}")
        except PermissionError as e:
            logger.error(f"Permission warning for deleting {file_full_path}: {e}")
            if not os.path.exists(file_full_path):
                logger.info(f"File {file_full_path} was deleted despite permission warning.")
            else:
                return jsonify({"error": f"Permission denied: {str(e)}"}), 500
        except Exception as e:
            logger.error(f"Error deleting file {file_full_path}: {e}")
            return jsonify({"error": str(e)}), 500

        if os.path.exists(tags_file):
            try:
                existing_tags = read_tags_file(tags_file)
                if current_name in existing_tags:
                    del existing_tags[current_name]
                    write_tags_file(tags_file, existing_tags)
                rel_path = os.path.relpath(full_path, ROOT_FOLDER).replace("\\", "/")
                full_item_path = os.path.join(rel_path, current_name).replace("\\", "/")
                update_root_tags(root_tags_file, full_item_path, None, action="delete")
            except PermissionError as e:
                logger.error(f"Permission denied updating {tags_file}: {e}")
                return jsonify({"error": f"Permission denied: {str(e)}. Grant write permissions to {tags_file}."}), 500
            except Exception as e:
                logger.error(f"Error updating tags for {tags_file}: {e}")
                return jsonify({"error": str(e)}), 500

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error deleting file {file_path}: {e}")
        return jsonify({"error": str(e)}), 500


# Search endpoint
@app.route('/api/search')
def search_files():
    try:
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({"error": "Please provide a search query."}), 400

        root_tags_file = os.path.join(ROOT_FOLDER, '.tags.txt')
        results = []
        if os.path.exists(root_tags_file):
            toggle_hidden_file(root_tags_file, hide=False)  # Unhide before reading
            try:
                with open(root_tags_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if ':' in line:
                            parts = line.strip().split(':', 3)
                            if len(parts) == 4:
                                full_path, file_format, tags, desc = parts
                                if (query in full_path.lower() or
                                        query in tags.lower() or
                                        query in desc.lower()):
                                    results.append({
                                        "name": os.path.basename(full_path),
                                        "path": full_path,
                                        "type": file_format,
                                        "tags": tags,
                                        "description": desc
                                    })
                logger.info(f"Successfully read and closed {root_tags_file}")
            except PermissionError as e:
                logger.error(f"Permission denied reading {root_tags_file}: {e}")
                return jsonify(
                    {"error": f"Permission denied: {str(e)}. Grant read permissions to {root_tags_file}."}), 500
            except Exception as e:
                logger.error(f"Error reading {root_tags_file}: {e}")
                return jsonify({"error": str(e)}), 500
            finally:
                toggle_hidden_file(root_tags_file, hide=True)  # Re-hide after reading

        return jsonify({"items": results, "breadcrumbs": [{"name": f"Search Results for '{query}'", "path": ""}]})
    except Exception as e:
        logger.error(f"Error searching files: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Run on startup: initialize tags for all non-hidden files, setting new files to "untagged" without AI processing
    initialize_tags()
    app.run(host='127.0.0.1', port=5000, debug=True)