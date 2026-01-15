import os
import uuid
import zipfile
import time
from flask import after_this_request
from flask import Flask, request, render_template, send_file, abort

app = Flask(__name__)

UPLOAD_PASSWORD = os.environ["UPLOAD_PASSWORD"]
INBOX_PASSWORD = os.environ["INBOX_PASSWORD"]


UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VALID_TOKENS = set()

EXPIRY_SECONDS = 24 * 60 * 60  # 24 hours

def cleanup_old_files():
    now = time.time()
    for f in os.listdir(UPLOAD_FOLDER):
        if not f.endswith(".zip"):
            continue

        path = os.path.join(UPLOAD_FOLDER, f)
        if now - os.path.getctime(path) > EXPIRY_SECONDS:
            os.remove(path)


# -------- Generate one-time upload link --------
@app.route("/generate")
def generate():
    token = str(uuid.uuid4())
    VALID_TOKENS.add(token)

    upload_url = request.host_url.rstrip("/") + f"/upload/{token}"
    inbox_url = request.host_url.rstrip("/") + "/inbox"

    return f"""
    <html>
    <body style="font-family:Arial;background:#f2f3f7;padding:20px">
        <div style="margin-bottom:20px">
            <a href="/generate">🔁 Generate New Link</a> |
            <a href="/inbox">📥 Inbox</a>
        </div>

        <h2>✅ Upload Link Generated</h2>
        <p>Share this link:</p>
        <p>
            <a href="{upload_url}" target="_blank">{upload_url}</a>
        </p>
        <p><b>Note:</b> Link works only once.</p>
    </body>
    </html>
    """



# -------- Upload page --------
@app.route("/upload/<token>", methods=["GET", "POST"])
def upload(token):
    if token not in VALID_TOKENS:
        abort(403)

    if request.method == "POST":
        if request.form.get("password") != UPLOAD_PASSWORD:
            abort(403)

        files = request.files.getlist("photos")
        files = [f for f in files if f.filename]

        if not files:
            abort(400)

        # CASE 1: 1–5 files → save individually
        if len(files) <= 5:
            for f in files:
                safe_name = f"{uuid.uuid4()}_{f.filename}"
                f.save(os.path.join(UPLOAD_FOLDER, safe_name))

        # CASE 2: 6+ files → ZIP
        else:
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
    
    cleanup_old_files()
    
    if request.method == "POST":
        if request.form.get("password") != INBOX_PASSWORD:
            return render_template("inbox.html", error="Wrong password")

        files = [
                    f for f in os.listdir(UPLOAD_FOLDER)
                    if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))
                ]           

        return render_template(
                "inbox.html",
                files=files,
                password=request.form.get("password"),
                base_url=request.host_url.rstrip("/")
            )


    return render_template("inbox.html")


# -------- Download --------
@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(path):
        abort(404)

    @after_this_request
    def remove_file(response):
        try:
            os.remove(path)
        except:
            pass
        return response

    return send_file(path, as_attachment=True)


#--------Delete from inbox -------

from flask import redirect, url_for

@app.route("/delete_all", methods=["POST"])
def delete_all():
    if request.form.get("password") != INBOX_PASSWORD:
        abort(403)

    for f in os.listdir(UPLOAD_FOLDER):
        if f.endswith(".zip"):
            os.remove(os.path.join(UPLOAD_FOLDER, f))

    return redirect(url_for("inbox"))



# -------- Run --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
