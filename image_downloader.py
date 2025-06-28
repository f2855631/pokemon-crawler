# 匯入必要的模組
import os
import json
import requests

# ---------- 設定圖片儲存資料夾 ----------
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)  # 若資料夾不存在就自動建立

# ---------- 錯誤圖片紀錄檔 ----------
missing_file = "missing_images.txt"
missing_list = []  # 用來儲存無法下載的圖片資訊

# ---------- 向官方 API 取得所有寶可夢的資料 ----------
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from=1&zukan_id_to=1025"

try:
    response = requests.get(API_URL, timeout=10)  # 設定 timeout 避免卡住
    response.raise_for_status()  # 若回應不是 200，會丟出例外
    raw_data = response.json().get("pokemons", [])  # 取出寶可夢資料陣列
    print(f"從 API 取得 {len(raw_data)} 筆資料")
except Exception as e:
    print(f"無法從 API 取得資料：{e}")
    exit(1)  # 若無法取得資料就終止程式

# ---------- 開始處理每一筆寶可夢圖片 ----------
total = len(raw_data)

for i, entry in enumerate(raw_data, 1):
    pokemon_id = entry.get("zukan_id")             # 主編號（例如 001）
    sub_id = entry.get("zukan_sub_id", 0)          # 子編號（例如 1、2，代表型態）
    image_url = entry.get("file_name", "").replace("\\", "/")  # 圖片連結，有時可能是反斜線

    # ---------- 若圖片連結為空或無效，就記錄錯誤 ----------
    if not image_url or image_url.startswith("images/"):
        print(f"無效圖片連結：{pokemon_id}_{sub_id} → {image_url}")
        missing_list.append(f"{pokemon_id}_{sub_id}: {image_url}")
        continue

    # ---------- 組合完整的圖片網址 ----------
    if image_url.startswith("/play") or image_url.startswith("/img"):
        full_url = f"https://tw.portal-pokemon.com{image_url}"
    else:
        full_url = image_url

    # ---------- 組合圖片檔名與儲存路徑 ----------
    image_filename = f"{pokemon_id}_{sub_id}.png"
    image_path = os.path.join(image_dir, image_filename)

    # ---------- 若圖片已存在，就跳過 ----------
    if os.path.exists(image_path):
        print(f"已存在：{image_filename}")
        continue

    # ---------- 嘗試下載圖片 ----------
    try:
        response = requests.get(full_url, timeout=10)

        # ---------- 若主網址 404，試試備用網址 ----------
        if response.status_code == 404 and image_url.startswith("/img"):
            backup_url = f"https://tw.portal-pokemon.com/play/resources/pokedex{image_url}"
            print(f"嘗試備用網址：{backup_url}")
            response = requests.get(backup_url, timeout=10)
            if response.status_code == 200:
                full_url = backup_url

        # ---------- 成功下載圖片 ----------
        if response.status_code == 200:
            with open(image_path, "wb") as f:
                f.write(response.content)
            print(f"已下載圖片（{i}/{total}）：{image_filename}")
        else:
            # ---------- 回應非 200，記錄錯誤 ----------
            print(f"下載失敗（{image_filename}） - 狀態碼 {response.status_code}")
            missing_list.append(f"{pokemon_id}_{sub_id}: {image_url} (status {response.status_code})")
    except Exception as e:
        # ---------- 發生例外，記錄錯誤 ----------
        print(f"下載錯誤（{image_filename}）：{e}")
        missing_list.append(f"{pokemon_id}_{sub_id}: {image_url} (error: {e})")

# ---------- 如果有錯誤圖片，輸出成一個記錄檔 ----------
if missing_list:
    with open(missing_file, "w", encoding="utf-8") as f:
        f.write("\n".join(missing_list))
    print(f"已記錄 {len(missing_list)} 筆錯誤到 {missing_file}")

# ---------- 全部結束 ----------
print("所有圖片處理完畢")
