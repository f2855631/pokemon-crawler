import time
import subprocess
from datetime import datetime

INTERVAL = 600  # 每隔幾秒執行一次（例如 600 秒 = 10 分鐘）

def has_git_changes():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    return result.stdout.strip() != ""

while True:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 開始執行爬蟲...")

    try:
        subprocess.run(["python", "crawler.py"])  # 執行爬蟲

        if has_git_changes():
            print("📂 偵測到檔案有變動，準備推送...")
            subprocess.run(["git", "add", "."])
            subprocess.run(["git", "commit", "-m", "Auto commit"])
            subprocess.run(["git", "push"])
            print("✅ 成功 Push 到 GitHub！")
        else:
            print("🟡 沒有檔案變動，不進行推送。")

    except Exception as e:
        print(f"⚠️ 發生錯誤：{e}")

    print(f"⏳ 等待 {INTERVAL} 秒後繼續...")
    time.sleep(INTERVAL)
