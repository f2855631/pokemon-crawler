import os
import json
import requests

# 圖片資料夾
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)

# 錯誤圖片記錄檔案
missing_file = "missing_images.txt"
missing_list = []

# 從 API 抓取圖鑑資料
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from=1&zukan_id_to=1025"
try:
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    raw_data = response.json().get("pokemons", [])
    print(f"🔄 從 API 取得 {len(raw_data)} 筆資料")
except Exception as e:
    print(f"❌ 無法從 API 取得資料：{e}")
    exit(1)

# 處理每筆寶可夢圖片下載
total = len(raw_data)
for i, entry in enumerate(raw_data, 1):
    pokemon_id = entry.get("zukan_id")
    sub_id = entry.get("zukan_sub_id", 0)
    image_url = entry.get("file_name", "").replace("\\", "/")

    if not image_url or image_url.startswith("images/"):
        print(f"⚠️ 無效圖片連結：{pokemon_id}_{sub_id} → {image_url}")
        missing_list.append(f"{pokemon_id}_{sub_id}: {image_url}")
        continue

    full_url = f"https://tw.portal-pokemon.com{image_url}" if image_url.startswith("/play") or image_url.startswith("/img") else image_url
    image_filename = f"{pokemon_id}_{sub_id}.png"
    image_path = os.path.join(image_dir, image_filename)

    # 如果圖片已經存在，就跳過
    if os.path.exists(image_path):
        print(f"✅ 已存在：{image_filename}")
        continue

    try:
        response = requests.get(full_url, timeout=10)

        # 如果主網址 404，嘗試改用 play/resources 路徑
        if response.status_code == 404 and image_url.startswith("/img"):
            backup_url = f"https://tw.portal-pokemon.com/play/resources/pokedex{image_url}"
            print(f"🔁 嘗試備用網址：{backup_url}")
            response = requests.get(backup_url, timeout=10)
            if response.status_code == 200:
                full_url = backup_url

        if response.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"🖼️ 已下載圖片（{i}/{total}）：{image_filename}")
        else:
            print(f"❌ 下載失敗（{image_filename}） - 狀態碼 {response.status_code}")
            missing_list.append(f"{pokemon_id}_{sub_id}: {image_url} (status {response.status_code})")
    except Exception as e:
        print(f"⚠️ 下載錯誤（{image_filename}）：{e}")
        missing_list.append(f"{pokemon_id}_{sub_id}: {image_url} (error: {e})")

# 輸出錯誤圖片紀錄
if missing_list:
    with open(missing_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing_list))
    print(f"📄 已記錄 {len(missing_list)} 筆錯誤到 {missing_file}")

print("🎉 所有圖片處理完畢")
