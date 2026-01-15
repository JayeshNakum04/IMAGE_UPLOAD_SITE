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
        abort(403)

    if request.method == "POST":
        if request.form.get("password") != UPLOAD_PASSWORD:
            abort(401)

        files = [f for f in request.files.getlist("photos") if f.filename]
        if not files:
            abort(400)

        upload_id = str(uuid.uuid4())
        zip_path = os.path.join(UPLOAD_FOLDER, f"{upload_id}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as zipf:
            for f in files:
                zipf.writestr(f.filename, f.read())

        TOKEN_STORE.remove(token)
        return "UPLOAD_OK"

    return render_template("upload.html")

# ======================
# INBOX LOGIN
# ======================
@app.route("/inbox", methods=["GET", "POST"])
def inbox():
    if request.method == "POST":
        if request.form.get("password") != INBOX_PASSWORD:
            return render_template(
                "inbox.html",
                logged_in=False,
                error="Wrong password"
            )

        uploads = []
        for f in os.listdir(UPLOAD_FOLDER):
            if f.endswith(".zip"):
                uploads.append({
                    "id": f,
                    "time": time.ctime(os.path.getctime(os.path.join(UPLOAD_FOLDER, f)))
                })

        return render_template(
            "inbox.html",
            logged_in=True,
            uploads=uploads
        )

    return render_template("inbox.html", logged_in=False)

# ======================
# DOWNLOAD + DELETE
# ======================
from flask import after_this_request

@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)

    @after_this_request
    def cleanup(response):
        try:
            os.remove(path)
        except:
            pass
        return response

    return send_file(path, as_attachment=True)


# ======================
# RUN (RENDER SAFE)
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
