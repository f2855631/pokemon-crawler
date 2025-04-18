import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep

# === 設定 ===
API_BATCH_SIZE = 100
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from={}&zukan_id_to={}"
DATA_FILE = "pokemon_data.json"
IMAGE_DIR = "images"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# === 初始化圖片資料夾 ===
os.makedirs(IMAGE_DIR, exist_ok=True)

# === 載入已存在的資料 ===
existing_data = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            for p in json.load(f):
                key = f"{p['id']}_{p.get('sub_id', 0)}"
                existing_data[key] = p
        print(f"🔍 已讀取本地 JSON：共 {len(existing_data)} 筆資料")
    except Exception as e:
        print(f"⚠️ 無法讀取 JSON：{e}，將跳過舊資料")
else:
    print("📂 未發現 pokemon_data.json，將建立全新資料")

# === 初始化 Selenium ===
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# === 抓取所有 API 資料 ===
all_api_data = []
for i in range(1, 1100, API_BATCH_SIZE):
    url = API_URL.format(i, i + API_BATCH_SIZE - 1)
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        all_api_data.extend(res.json())

# === 去除重複項目 ===
unique_keys = set()
for item in all_api_data:
    if isinstance(item, dict) and 'zukan_id' in item and 'zukan_sub_id' in item:
        pid = item['zukan_id']
        subid = item['zukan_sub_id']
        unique_keys.add(f"{pid}_{subid}")
    else:
        print(f"⚠️ 非預期資料格式，略過：{item}")

# === 爬取細節資料 ===
new_data = []
for key in sorted(unique_keys):
    if key in existing_data:
        print(f"✅ 資料已存在：{key}")
        continue

    pid, subid = key.split("_")
    url = f"https://tw.portal-pokemon.com/play/pokedex/{pid}" + (f"_{subid}" if subid != "0" else "")
    print(f"🔍 抓取細節頁面：{url}")
    driver.get(url)
    sleep(1)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one(".contents.pokemon-detail-contents")
    if not container:
        print(f"⛔ 無效頁面：{url}")
        continue

    name_tag = soup.select_one(".pokemon-slider__main-name")
    name = name_tag.text.strip() if name_tag else "未知"

    category_tag = soup.select_one(".pokemon-info__category")
    category = category_tag.text.strip() if category_tag else ""

    gender_tag = soup.select_one(".pokemon-info__gender-icon")
    gender = "male/female" if gender_tag else "unknown"

    skill_tags = soup.select(".pokemon-move__title")
    skills = [s.text.strip() for s in skill_tags if s.text.strip()]

    img_filename = f"{pid}_{subid}.png"
    img_url = f"https://tw.portal-pokemon.com/play/resources/pokedex/img/pm_{pid}_{int(subid):02}.png"
    img_path = os.path.join(IMAGE_DIR, img_filename)

    if not os.path.exists(img_path):
        img_res = requests.get(img_url)
        if img_res.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(img_res.content)
            print(f"🖼️ 圖片已下載：{img_filename}")
        else:
            print(f"⚠️ 圖片下載失敗：{img_url}")

    entry = {
        "id": pid,
        "sub_id": int(subid),
        "name": name,
        "category": category,
        "gender": gender,
        "skills": skills,
        "local_image_path": img_path
    }
    existing_data[key] = entry
    new_data.append(entry)
    print(f"✅ 已新增：{name} ({key})")

# === 寫入 JSON ===
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(list(existing_data.values()), f, ensure_ascii=False, indent=2)

driver.quit()

# 合併原本資料 + 新資料後存檔
all_pokemon = existing_data + pokemon_list
with open("pokemon_data.json", "w", encoding="utf-8") as f:
    json.dump(all_pokemon, f, ensure_ascii=False, indent=2)
