from huggingface_hub import create_repo, upload_folder
from pathlib import Path

# Edit these variables if you want a different repo name
REPO_ID = "bayan10/summarization-model"
FOLDER_PATH = r"D:\BAYAN\models\Summarization\Model"

print(f"Creating repo {REPO_ID} (if it doesn't exist)")
create_repo(REPO_ID, repo_type="model", exist_ok=True)

print(f"Uploading folder {FOLDER_PATH} to {REPO_ID}...")
upload_folder(repo_id=REPO_ID, folder_path=FOLDER_PATH, repo_type="model")

print("Upload complete. Visit: https://huggingface.co/" + REPO_ID)
