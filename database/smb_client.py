from smb.SMBConnection import SMBConnection as SC
from dotenv import load_dotenv
import os
import tempfile

load_dotenv()

SERVER_IP = os.getenv("SERVER_IP")
SERVER_NAME = os.getenv("SERVER_NAME")
SHARE_NAME = os.getenv("SHARE_NAME")
SAMPLE_FOLDER = os.getenv("SAMPLE_FOLDER")
SAMPLE_FILE = os.getenv("SAMPLE_FILE")
SAMBA_USERNAME = os.getenv("SAMBA_USERNAME")
SAMBA_PASSWORD = os.getenv("SAMBA_PASSWORD")


class SambaClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.conn = SC(
                SAMBA_USERNAME,
                SAMBA_PASSWORD,
                "calibrax_client",
                SERVER_IP,
                use_ntlm_v2=True,
            )
            assert cls._instance.conn.connect(SERVER_IP, 139)
        return cls._instance

    def get_file(self, remote_path):
        """获取指定路径的文件内容"""
        tf = tempfile.NamedTemporaryFile(delete=False)
        try:
            with open(tf.name, "wb") as f:
                self._instance.conn.retrieveFile(SHARE_NAME, remote_path, f)
            with open(tf.name, "rb") as f:
                content = [l.decode("utf-8").strip() for l in f.readlines()]
            os.remove(tf.name)  # 删除临时文件
            if not content:
                print(f"File {remote_path} is empty or does not exist.")
                return None

            return content
        except Exception as e:
            print(f"Error reading file: {e}")
            return None

    def get_files_in_folder(self, folder=SAMPLE_FOLDER):
        files = self._instance.conn.listPath(SHARE_NAME, folder)
        return [file.filename for file in files if not file.isDirectory]

    def download_file(self, remote_path, local_path):
        """下载指定路径的文件到本地"""
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                self._instance.conn.retrieveFile(SHARE_NAME, remote_path, f)
        except Exception as e:
            print(f"Error downloading file: {e}")
            return None
        return local_path

    def close(self):
        self._instance.conn.close()


if __name__ == "__main__":
    sc = SambaClient()
    # fs = sc.get_files_in_folder()
    # print("Files in folder:", fs)
    # sc.download_file(f"{SAMPLE_FOLDER}/{SAMPLE_FILE}", "./downloaded_file.csv")
    # print("File downloaded successfully.")
    f = sc.get_file(f"{SAMPLE_FOLDER}/{SAMPLE_FILE}")
    if f:
        print("File content:", f[:100])
    else:
        print("Failed to retrieve file content.")
    sc.close()
    # print("Connection closed.")
