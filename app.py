import os
import uuid
import zipfile
import time
from flask import Flask, render_template, request, send_file, abort, redirect, url_for

app = Flask(__name__)

# ======================
# ENV CONFIG
# ======================
UPLOAD_PASSWORD = os.environ.get("UPLOAD_PASSWORD")
INBOX_PASSWORD = os.environ.get("INBOX_PASSWORD")

if not UPLOAD_PASSWORD or not INBOX_PASSWORD:
    raise RuntimeError("Required environment variables not set")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TOKEN_STORE = set()
EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours

# ======================
# UTIL: CLEANUP OLD FILES
# ======================
def cleanup_expired_uploads():
    now = time.time()
    for folder in os.listdir(UPLOAD_FOLDER):
        path = os.path.join(UPLOAD_FOLDER, folder)
        if not os.path.isdir(path):
            continue

        created = os.path.getctime(path)
        if now - created > EXPIRY_SECONDS:
            for f in os.listdir(path):
                os.remove(os.path.join(path, f))
            os.rmdir(path)

# ======================
# GENERATE ONE-TIME LINK
# ======================
@app.route("/generate")
def generate():
    token = str(uuid.uuid4())
    TOKEN_STORE.add(token)
    return f"""
    <h3>One-time upload link</h3>
    <a href="/upload/{token}">/upload/{token}</a><br><br>
    <a href="/inbox">Inbox</a>
    """

# ======================
# UPLOAD PAGE (FRIEND)
# ======================
@app.route("/upload/<token>", methods=["GET", "POST"])
def upload(token):
    if token not in TOKEN_STORE:
        abort(403, "Invalid or used link")

    if request.method == "POST":
        password = request.form.get("password")
        if password != UPLOAD_PASSWORD:
            abort(401)

        files = [f for f in request.files.getlist("photos") if f.filename]
        if not files:
            abort(400)

        upload_id = str(uuid.uuid4())
        folder = os.path.join(UPLOAD_FOLDER, upload_id)
        os.makedirs(folder)

        for f in files:
            f.save(os.path.join(folder, f.filename))

        TOKEN_STORE.remove(token)
        return "<h3>Upload successful ✅</h3>"

    return render_template("upload.html")

# ======================
# INBOX LOGIN
# ======================
@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    cleanup_expired_uploads()

    if request.method == "POST":
        if request.form.get("password") != INBOX_PASSWORD:
            abort(401)

        uploads = sorted(
            os.listdir(UPLOAD_FOLDER),
            key=lambda x: os.path.getctime(os.path.join(UPLOAD_FOLDER, x)),
            reverse=True
        )

        data = []
        for u in uploads:
            path = os.path.join(UPLOAD_FOLDER, u)
            data.append({
                "id": u,
                "time": time.ctime(os.path.getctime(path))
            })

        return render_template("inbox.html", uploads=data)

    return render_template("inbox_login.html")

# ======================
# DOWNLOAD + DELETE
# ======================
@app.route("/download/<upload_id>")
def download(upload_id):
    folder = os.path.join(UPLOAD_FOLDER, upload_id)
    if not os.path.exists(folder):
        abort(404)

    zip_path = f"{folder}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zipf:
        for f in os.listdir(folder):
            zipf.write(os.path.join(folder, f), f)

    for f in os.listdir(folder):
        os.remove(os.path.join(folder, f))
    os.rmdir(folder)

    return send_file(zip_path, as_attachment=True)

@app.route("/__routes")
def show_routes():
    return "<br>".join(sorted(rule.rule for rule in app.url_map.iter_rules()))

# ======================
# RUN (RENDER SAFE)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
