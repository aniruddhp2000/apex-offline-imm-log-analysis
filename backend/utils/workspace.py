import os
import uuid
import zipfile
import shutil

class WorkspaceManager:
    def __init__(self, base_dir=None):
        if base_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
            base_dir = os.path.join(project_root, "workspaces")
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        session_path = os.path.join(self.base_dir, session_id)
        os.makedirs(session_path, exist_ok=True)
        # Create upload and extracted directories
        os.makedirs(os.path.join(session_path, "upload"), exist_ok=True)
        os.makedirs(os.path.join(session_path, "extracted"), exist_ok=True)
        return session_id

    def get_session_dir(self, session_id: str) -> str:
        return os.path.join(self.base_dir, session_id)

    def get_extracted_dir(self, session_id: str) -> str:
        return os.path.join(self.base_dir, session_id, "extracted")

    def get_upload_dir(self, session_id: str) -> str:
        return os.path.join(self.base_dir, session_id, "upload")

    def save_uploaded_file(self, session_id: str, filename: str, content: bytes) -> str:
        upload_dir = self.get_upload_dir(session_id)
        file_path = os.path.join(upload_dir, filename)
        with open(file_path, "wb") as f:
            f.write(content)
        return file_path

    def extract_archive(self, session_id: str, file_path: str) -> str:
        extracted_dir = self.get_extracted_dir(session_id)
        
        # Check if the file is a zip
        if zipfile.is_zipfile(file_path):
            with zipfile.ZipFile(file_path, 'r') as z:
                z.extractall(extracted_dir)
            
            # Post-processing: If there are nested zip files, extract them too!
            self._recursive_extract(extracted_dir)
        else:
            # If not a zip, just copy it to the extracted folder
            dest = os.path.join(extracted_dir, os.path.basename(file_path))
            shutil.copy2(file_path, dest)
            
        return extracted_dir

    def _recursive_extract(self, directory: str):
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.zip'):
                    zip_path = os.path.join(root, file)
                    # Extract to a subfolder named after the zip
                    target_subfolder = os.path.join(root, file[:-4])
                    os.makedirs(target_subfolder, exist_ok=True)
                    try:
                        with zipfile.ZipFile(zip_path, 'r') as z:
                            z.extractall(target_subfolder)
                        # Remove the zip file after successful extraction to clean up
                        os.remove(zip_path)
                        # Recursively extract contents of this new folder
                        self._recursive_extract(target_subfolder)
                    except Exception as e:
                        print(f"Error extracting nested zip {file}: {e}")

    def clean_session(self, session_id: str):
        """
        Deletes a session directory and all its contents.
        """
        session_path = self.get_session_dir(session_id)
        if os.path.exists(session_path):
            shutil.rmtree(session_path)

    def list_sessions(self) -> list:
        """
        Scans the workspaces directory and returns a list of dictionaries 
        containing metadata for all past analysis sessions.
        """
        sessions = []
        if not os.path.exists(self.base_dir):
            return sessions

        for session_id in os.listdir(self.base_dir):
            session_path = os.path.join(self.base_dir, session_id)
            if not os.path.isdir(session_path):
                continue
                
            summary_path = os.path.join(session_path, "summary.json")
            if os.path.exists(summary_path):
                try:
                    import json
                    with open(summary_path, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                    
                    # Fetch basic stats for the history view
                    sessions.append({
                        "session_id": session_id,
                        "timestamp": summary.get("timestamp", os.path.getctime(summary_path)),
                        "file_count": summary.get("discovered_files", 0),
                        "crashes": summary.get("crashes_count", 0),
                        "http_errors": summary.get("http_errors_count", 0),
                        "products": summary.get("detected_products", []),
                        "name": summary.get("name", "Log Analysis")
                    })
                except Exception as e:
                    print(f"Error reading summary for session {session_id}: {e}")
        
        # Sort sessions newest first
        sessions.sort(key=lambda x: x["timestamp"], reverse=True)
        return sessions
