import json
import os
import time
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# === 設定 API 參數 ===
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1"
ZUKAN_FROM = 1
ZUKAN_TO = 1025

# === 啟動 Selenium ===
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# === 載入已有資料 ===
data_file = "pokemon_data.json"
existing_data = {}
if os.path.exists(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        try:
            loaded = json.load(f)
            for entry in loaded:
                if "id" in entry:
                    key = f"{entry['id']}_{entry.get('sub_id', '00')}"
                    existing_data[key] = entry
                else:
                    print(f"⚠️ 找不到 id，略過該筆：{entry.get('pokemon_name', '未知')}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON 解析錯誤：{e}")
            loaded = []

# === API 抓取資料 ===
params = {
    "pokemon_ability_id": "",
    "zukan_id_from": ZUKAN_FROM,
    "zukan_id_to": ZUKAN_TO
}
response = requests.get(API_URL, params=params)
if response.status_code != 200:
    print("❌ API 請求失敗")
    exit()

api_data = response.json()
new_data = []
os.makedirs("images", exist_ok=True)

for item in api_data:
    zukan_id = item.get("zukan_id")
    zukan_sub_id = item.get("zukan_sub_id", "00")
    unique_key = f"{zukan_id}_{zukan_sub_id}"

    if unique_key in existing_data:
        print(f"✅ 已存在 {item['pokemon_name']}（{unique_key}），跳過")
        continue

    print(f"🔄 補抓 {item['pokemon_name']} 的詳細資料...")
    detail_url = f"https://tw.portal-pokemon.com/play/pokedex/{str(zukan_id).zfill(4)}"
    driver.get(detail_url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 分類
    category_tag = soup.select_one(".pokemon-info__category .pokemon-info__value span")
    category = category_tag.text.strip() if category_tag else "N/A"

    # 性別
    gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
    gender_list = []
    for icon in gender_icons:
        src = icon.get("src", "")
        if "male" in src:
            gender_list.append("♂")
        elif "female" in src:
            gender_list.append("♀")
    gender = " / ".join(gender_list) if gender_list else "無性別"

    # 身高
    height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
    height = height_tag.text.strip() if height_tag else "N/A"

    # 體重
    weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")
    weight = weight_tag.text.strip() if weight_tag else "N/A"

    # 特性
    ability_tag = soup.select_one(".pokemon-info__abilities .pokemon-info__value")
    if ability_tag:
        ability_text = ability_tag.get_text(strip=True)
        abilities = [a.strip() for a in ability_text.replace("\n", "").split("／")]
    else:
        abilities = []

    # 弱點
    weakness_tags = soup.select(".pokemon-weakness__items .pokemon-weakness__btn span")
    weaknesses = [w.text.strip() for w in weakness_tags if w.text.strip()]

    # 圖片下載
    img_url = item.get("pokemon_photo")
    img_name = f"{str(zukan_id).zfill(4)}_{item['pokemon_name']}.png"
    img_path = os.path.join("images", img_name)
    if img_url and not os.path.exists(img_path):
        try:
            img_data = requests.get(img_url, timeout=10)
            img_data.raise_for_status()
            with open(img_path, "wb") as f:
                f.write(img_data.content)
            print(f"🖼️ 圖片已下載：{img_name}")
        except Exception as e:
            print(f"❌ 圖片下載失敗：{img_name}，錯誤：{e}")
            img_path = ""  # 記錄為空字串，方便後續辨識

    # 儲存欄位轉換
    item["id"] = zukan_id
    item["sub_id"] = zukan_sub_id
    item.pop("zukan_id", None)
    item.pop("zukan_sub_id", None)

    # 組合資料
    item["category"] = category
    item["gender"] = gender
    item["height"] = height
    item["weight"] = weight
    item["pokemon_ability"] = abilities
    item["weaknesses"] = weaknesses
    item["local_image"] = img_path

    new_data.append(item)

# === 合併儲存資料 ===
all_data = list(existing_data.values()) + new_data
with open(data_file, "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False, indent=2)

driver.quit()
print("✅ 全部完成！")
