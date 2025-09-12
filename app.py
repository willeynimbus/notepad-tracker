from flask import Flask, render_template, request, jsonify
import os
import git
import time
import json
from datetime import datetime

app = Flask(__name__)

# Path where files will be saved (in project directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Current project directory
NOTES_DIR = os.path.join(BASE_DIR, "notes")
METADATA_FILE = os.path.join(BASE_DIR, "notes_metadata.json")

# Create directories if they don't exist
for directory in [BASE_DIR, NOTES_DIR]:
    if not os.path.exists(directory):
        os.makedirs(directory)

# Initialize Git repo
if not os.path.exists(os.path.join(BASE_DIR, ".git")):
    repo = git.Repo.init(BASE_DIR)
    # Create initial commit
    gitignore_path = os.path.join(BASE_DIR, ".gitignore")
    with open(gitignore_path, "w") as f:
        f.write("__pycache__/\n*.pyc\n.env\n")
    repo.index.add([gitignore_path])
    repo.index.commit("Initial commit")
else:
    repo = git.Repo(BASE_DIR)

def load_notes_metadata():
    """Load notes metadata from JSON file"""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_notes_metadata(metadata):
    """Save notes metadata to JSON file"""
    with open(METADATA_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

def generate_filename(title):
    """Generate a safe filename from title"""
    # Remove special characters and replace spaces with underscores
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{safe_title}.txt"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/notes", methods=["GET"])
def get_notes():
    """Get all notes metadata"""
    metadata = load_notes_metadata()
    return jsonify(metadata)

@app.route("/save", methods=["POST"])
def save_file():
    data = request.json
    title = data.get("title", "Untitled Note").strip()
    content = data.get("content", "")
    note_id = data.get("note_id")  # For existing notes
    
    metadata = load_notes_metadata()
    
    if note_id and note_id in metadata:
        # Update existing note
        filename = metadata[note_id]["filename"]
        metadata[note_id]["updated_at"] = datetime.now().isoformat()
        metadata[note_id]["title"] = title
    else:
        # Create new note
        filename = generate_filename(title)
        note_id = str(int(time.time() * 1000))  # Use timestamp as ID
        metadata[note_id] = {
            "id": note_id,
            "title": title,
            "filename": filename,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
    
    file_path = os.path.join(NOTES_DIR, filename)
    
    # Write the note content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"Title: {title}\n")
        f.write(f"Created: {metadata[note_id]['created_at']}\n")
        f.write(f"Updated: {metadata[note_id]['updated_at']}\n")
        f.write("-" * 50 + "\n\n")
        f.write(content)
    
    # Save metadata
    save_notes_metadata(metadata)
    
    try:
        # Git add & commit
        repo.index.add([file_path, METADATA_FILE])
        commit_message = f"{'Update' if note_id in load_notes_metadata() else 'Add'} note: {title}"
        repo.index.commit(commit_message)
        
        # Push to remote if configured
        try:
            if repo.remotes:
                origin = repo.remote('origin')
                origin.push()
                git_status = "Pushed to GitHub"
            else:
                git_status = "Committed locally (no remote configured)"
        except Exception as e:
            git_status = f"Committed locally (push failed: {str(e)})"
            
    except Exception as e:
        git_status = f"Git error: {str(e)}"
    
    return jsonify({
        "message": "Note saved successfully",
        "note_id": note_id,
        "filename": filename,
        "git_status": git_status
    })

@app.route("/load/<note_id>", methods=["GET"])
def load_note(note_id):
    """Load a specific note by ID"""
    metadata = load_notes_metadata()
    
    if note_id not in metadata:
        return jsonify({"error": "Note not found"}), 404
    
    note_info = metadata[note_id]
    file_path = os.path.join(NOTES_DIR, note_info["filename"])
    
    if not os.path.exists(file_path):
        return jsonify({"error": "Note file not found"}), 404
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract content after the header
    lines = content.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if line.startswith('-' * 20):  # Find the separator line
            content_start = i + 2  # Skip separator and empty line
            break
    
    actual_content = '\n'.join(lines[content_start:])
    
    return jsonify({
        "note_id": note_id,
        "title": note_info["title"],
        "content": actual_content,
        "created_at": note_info["created_at"],
        "updated_at": note_info["updated_at"]
    })

@app.route("/delete/<note_id>", methods=["DELETE"])
def delete_note(note_id):
    """Delete a note"""
    metadata = load_notes_metadata()
    
    if note_id not in metadata:
        return jsonify({"error": "Note not found"}), 404
    
    note_info = metadata[note_id]
    file_path = os.path.join(NOTES_DIR, note_info["filename"])
    
    # Delete file if exists
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Remove from metadata
    del metadata[note_id]
    save_notes_metadata(metadata)
    
    try:
        # Git commit the deletion
        repo.index.remove([file_path])
        repo.index.add([METADATA_FILE])
        repo.index.commit(f"Delete note: {note_info['title']}")
        
        if repo.remotes:
            origin = repo.remote('origin')
            origin.push()
            git_status = "Deletion pushed to GitHub"
        else:
            git_status = "Deletion committed locally"
            
    except Exception as e:
        git_status = f"Git error: {str(e)}"
    
    return jsonify({
        "message": "Note deleted successfully",
        "git_status": git_status
    })

if __name__ == "__main__":
    app.run(debug=True)