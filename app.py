import os
import uuid
import zipfile
from io import BytesIO
from flask import Flask, render_template, request, send_file, abort

app = Flask(__name__)

# =========================
# 🔐 Secure password (ENV)
# =========================
UPLOAD_PASSWORD = os.environ.get("UPLOAD_PASSWORD")
if not UPLOAD_PASSWORD:
    raise RuntimeError("UPLOAD_PASSWORD not set")

# =========================
# 🔗 One-time tokens (RAM)
# =========================
valid_tokens = set()

# =========================
# Generate one-time link
# =========================
@app.route("/generate")
def generate_link():
    token = str(uuid.uuid4())
    valid_tokens.add(token)
    return (
        "One-time upload link (valid for ONE use only):<br><br>"
        f"<a href='/upload/{token}'>/upload/{token}</a>"
    )

# =========================
# Upload route (token-based)
# =========================
@app.route("/upload/<token>", methods=["GET", "POST"])
def upload_with_token(token):

    # ❌ invalid or already-used token
    if token not in valid_tokens:
        abort(403, "This upload link is invalid or already used")

    if request.method == "POST":

        # 🔐 Password validation
        password = request.form.get("password")
        if password != UPLOAD_PASSWORD:
            abort(401, "Invalid password")

        # Get valid files only
        files = [
            f for f in request.files.getlist("photos")
            if f and f.filename.strip()
        ]

        if not files:
            abort(400, "No files uploaded")

        # 🔥 Invalidate token immediately (ONE-TIME)
        valid_tokens.remove(token)

        # ======================
        # CASE 1: >5 files → ZIP
        # ======================
        if len(files) > 5:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_STORED) as zipf:
                for file in files:
                    zipf.writestr(file.filename, file.read())

            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name="photos.zip"
            )

        # ======================
        # CASE 2: 1–5 → SINGLE
        # ======================
        img = files[0]
        img_buffer = BytesIO(img.read())
        img_buffer.seek(0)

        return send_file(
            img_buffer,
            as_attachment=True,
            download_name=img.filename
        )

    return render_template("upload.html")


# =========================
# Run locally
# =========================
if __name__ == "__main__":
    app.run()

