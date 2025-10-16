from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uuid, os, json
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Document Source API")
app.mount("/static", StaticFiles(directory="static"), name="UI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "data.json"
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Load existing file metadata
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        documents = json.load(f)
else:
    documents = []

# Redirect root to UI
@app.get("/")
def root():
    return RedirectResponse(url="/static/UI.html")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    filename = file.filename
    file_path = os.path.join(UPLOAD_DIR, file_id + "_" + filename)

    # Save file locally
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Store metadata
    doc_meta = {
        "id": file_id,
        "filename": filename,
        "content_type": file.content_type,
        "download_url": f"/files/{file_id}",
    }
    documents.append(doc_meta)

    with open(DATA_FILE, "w") as f:
        json.dump(documents, f, indent=4)

    return {"message": "File uploaded", "id": file_id}

@app.get("/documents")
def list_documents():
    """Return list of files metadata only"""
    return documents

@app.get("/files/{doc_id}")
def get_file(doc_id: str):
    """Return raw file for download"""
    doc = next((d for d in documents if d["id"] == doc_id), None)
    if not doc:
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{doc['filename']}")
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "File missing"})
    
    from fastapi.responses import FileResponse
    return FileResponse(file_path, media_type=doc["content_type"], filename=doc["filename"])

@app.delete("/delete/{doc_id}")
def delete_file(doc_id: str):
    """Delete a file by ID"""
    global documents
    doc = next((d for d in documents if d["id"] == doc_id), None)
    if not doc:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    file_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{doc['filename']}")
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove metadata
    documents = [d for d in documents if d["id"] != doc_id]
    with open(DATA_FILE, "w") as f:
        json.dump(documents, f, indent=4)

    return {"message": "File deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
