import os
import uuid
import zipfile
from flask import Flask, request, render_template, send_file, abort

app = Flask(__name__)

UPLOAD_PASSWORD = os.environ.get("UPLOAD_PASSWORD", "2409004")
INBOX_PASSWORD = os.environ.get("INBOX_PASSWORD", "admin123")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VALID_TOKENS = set()

# -------- Generate one-time upload link --------
@app.route("/generate")
def generate():
    token = str(uuid.uuid4())
    VALID_TOKENS.add(token)
    return f"Upload link: /upload/{token}"

# -------- Upload page --------
@app.route("/upload/<token>", methods=["GET", "POST"])
def upload(token):
    if token not in VALID_TOKENS:
        abort(403)

    if request.method == "POST":
        if request.form.get("password") != UPLOAD_PASSWORD:
            abort(403)

        files = request.files.getlist("photos")
        if not files or files[0].filename == "":
            abort(400)

        upload_id = str(uuid.uuid4())
        zip_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zipf:
            for f in files:
                zipf.writestr(f.filename, f.read())

        VALID_TOKENS.remove(token)
        return "Upload successful. You can close this page."

    return render_template("upload.html")

# -------- Inbox --------
@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    if request.method == "POST":
        if request.form.get("password") != INBOX_PASSWORD:
            return render_template("inbox.html", error="Wrong password")

        files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith(".zip")]
        return render_template("inbox.html", files=files, password=request.form.get("password"))

    return render_template("inbox.html")


# -------- Download --------
@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)
    return send_file(path, as_attachment=True)

#--------Delete from inbox -------

@app.route("/delete_all", methods=["POST"])
def delete_all():
    if request.form.get("password") != INBOX_PASSWORD:
        abort(403)

    for f in os.listdir(UPLOAD_FOLDER):
        if f.endswith(".zip"):
            os.remove(os.path.join(UPLOAD_FOLDER, f))

    return "Deleted"


# -------- Run --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
