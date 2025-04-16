import time
import subprocess
from datetime import datetime

INTERVAL = 600  # 每隔幾秒執行一次（600 = 10分鐘）

def has_git_changes():
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    return result.stdout.strip() != ""

while True:
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ⏱ 正在檢查是否有變動...")

    try:
        if has_git_changes():
            print("📂 偵測到有變動，開始執行爬蟲...")
            subprocess.run(["python", "crawler.py"])
            
            print("📤 推送變更中...")
            subprocess.run(["git", "add", "."])
            subprocess.run(["git", "commit", "-m", "Auto commit"])
            subprocess.run(["git", "push"])
            print("✅ 成功 Push 到 GitHub！")
        else:
            print("🟡 沒有變動，跳過爬蟲與推送。")
    except Exception as e:
        print(f"⚠️ 發生錯誤：{e}")

    print(f"⏳ 等待 {INTERVAL} 秒後繼續...")
    time.sleep(INTERVAL)
