from flask import Flask, render_template, request, jsonify
import os
import git
import time

app = Flask(__name__)

# Path where files will be saved
BASE_DIR = os.path.expanduser("~/notepad_tracker_files")
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Initialize Git repo
if not os.path.exists(os.path.join(BASE_DIR, ".git")):
    repo = git.Repo.init(BASE_DIR)
else:
    repo = git.Repo(BASE_DIR)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save_file():
    data = request.json
    filename = data.get("filename", "note.txt")
    content = data.get("content", "")

    file_path = os.path.join(BASE_DIR, filename)

    with open(file_path, "w") as f:
        f.write(content)

    # Git add & commit
    repo.index.add([file_path])
    repo.index.commit(f"Auto-save at {time.strftime('%Y-%m-%d %H:%M:%S')}")

    return jsonify({"message": "File saved and committed", "file": filename})

if __name__ == "__main__":
    app.run(debug=True)
