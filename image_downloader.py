import os
import json
import requests
from bs4 import BeautifulSoup

image_dir = "images"
data_file = "pokemon_data.json"
os.makedirs(image_dir, exist_ok=True)

# 檢查 JSON 是否存在
if not os.path.exists(data_file):
    print("❌ 找不到 pokemon_data.json，請先執行 json_updater.py")
    exit(1)

# 讀取資料
with open(data_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# 逐筆處理
for entry in data:
    pokemon_id = entry.get("id")
    sub_id = entry.get("sub_id", 0)
    key = f"{pokemon_id}_{sub_id}"
    image_filename = f"{pokemon_id}_{sub_id}.png"
    image_path = os.path.join(image_dir, image_filename)

    # 已有圖片就跳過
    if os.path.exists(image_path):
        print(f"⏭️ 已有圖片：{image_filename}")
        continue

    # 抓圖
    url = f"https://tw.portal-pokemon.com/play/pokedex/{pokemon_id}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            print(f"❌ 無法開啟網頁：{url}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        img_tag = soup.select_one(".pokemon-img__front")
        img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else ""
        if img_url.startswith("/"):
            img_url = "https://tw.portal-pokemon.com" + img_url

        if img_url:
            img_data = requests.get(img_url, timeout=10)
            if img_data.status_code == 200:
                with open(image_path, "wb") as f:
                    f.write(img_data.content)
                print(f"✅ 已下載圖片：{image_filename}")
                entry["image"] = image_path
            else:
                print(f"⚠️ 圖片下載失敗：{img_url}")
        else:
            print(f"⚠️ 找不到圖片標籤：{key}")

    except Exception as e:
        print(f"❌ 抓取 {key} 發生錯誤：{e}")

# 儲存更新後的 JSON
with open(data_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("📦 圖片下載流程結束")
