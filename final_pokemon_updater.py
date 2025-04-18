import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep

API_BATCH_SIZE = 100
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from={}&zukan_id_to={}"
DATA_FILE = "pokemon_data.json"
IMAGE_DIR = "images"
HEADERS = {"User-Agent": "Mozilla/5.0"}

os.makedirs(IMAGE_DIR, exist_ok=True)

# 安全讀取本地資料
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

# 初始化 Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# 呼叫 API 並安全處理
all_api_data = []
for i in range(1, 1100, API_BATCH_SIZE):
    url = API_URL.format(i, i + API_BATCH_SIZE - 1)
    print(f"🌐 呼叫 API：{url}")
    try:
        res = requests.get(url, headers=HEADERS)
        if res.status_code == 200:
            try:
                batch = res.json()
                if isinstance(batch, dict) and 'pokemons' in batch and isinstance(batch['pokemons'], list):
                    all_api_data.extend(batch['pokemons'])
                    print(f"✅ 拿到 {len(batch['pokemons'])} 筆資料")
                else:
                    print(f"⚠️ 回傳格式錯誤：{type(batch)}，內容：{batch}")
            except Exception as e:
                print(f"❌ 解析 JSON 失敗：{e}")
        else:
            print(f"❌ API 回傳狀態碼：{res.status_code}")
    except Exception as e:
        print(f"❌ 請求失敗：{e}")

# 建立 key 清單
unique_keys = set()
for item in all_api_data:
    if isinstance(item, dict) and 'zukan_id' in item and 'zukan_sub_id' in item:
        pid = item['zukan_id']
        subid = item['zukan_sub_id']
        unique_keys.add(f"{pid}_{subid}")
    else:
        print(f"⚠️ 非預期資料格式：{item}")

# 執行爬蟲
new_data = []
for key in sorted(unique_keys):
    if key in existing_data:
        old = existing_data[key]
        if all(k in old and old[k] for k in ["height", "weight", "abilities", "weaknesses"]):
            print(f"✅ 已存在：{key}（資料完整，略過）")
            continue
        else:
            print(f"🔁 已存在但資料不完整，重新抓取：{key}")

    pid, subid = key.split("_")
    url = f"https://tw.portal-pokemon.com/play/pokedex/{pid}" + (f"_{subid}" if subid != "0" else "")
    print(f"🔍 抓取：{url}")
    driver.get(url)
    sleep(1.5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    container = soup.select_one(".contents.pokemon-detail-contents")
    if not container:
        print(f"⛔ 無效頁面：{url}")
        continue

    name_tag = soup.select_one(".pokemon-slider__main-name")
    category_tag = soup.select_one(".pokemon-info__category")

    # 解析性別圖示（新版以 src 判斷）
    gender_icons = soup.select(".pokemon-info__gender-icon")
    sources = [img.get("src", "") for img in gender_icons]

    male = any("male" in src for src in sources)
    female = any("female" in src for src in sources)

    if male and female:
        gender = "♂ / ♀"
    elif male:
        gender = "♂"
    elif female:
        gender = "♀"
    else:
        gender = """♂ / ♀"
elif male:
    gender = "♂"
elif female:
    gender = "♀"
else:
    gender = """♂ / ♀"
    elif male:
        gender = "♂"
    elif female:
        gender = "♀"
    else:
        gender = ""soup.select_one(".pokemon-info__gender-icon")
    if gender_block:
        male = gender_block.find("img", {"alt": "雄性"})
        female = gender_block.find("img", {"alt": "雌性"})
        if male and female:
            gender = "♂ / ♀"
        elif male:
            gender = "♂"
        elif female:
            gender = "♀"
        else:
            gender = ""
    else:
        gender = ""

    # 特性、身高、體重
    ability_tag = soup.select_one(".pokemon-info__abilities .pokemon-info__value")
    abilities = ability_tag.contents[0].strip().split(" / ") if ability_tag and ability_tag.contents else [].pokemon-info__value span")
    abilities = [a.text.strip() for a in ability_tags if a.text.strip()]

    height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
    weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")

    weakness_tags = soup.select(".pokemon-weakness__btn span")
    weaknesses = [w.text.strip() for w in weakness_tags if w.text.strip()]

    name = name_tag.text.strip() if name_tag else "未知"
    category = category_tag.text.strip() if category_tag else ""
    height = height_tag.text.strip() if height_tag else ""
    weight = weight_tag.text.strip() if weight_tag else ""

    img_tag = soup.select_one(".pokemon-img__front")
    if img_tag and img_tag.get("src"):
        img_url = "https://tw.portal-pokemon.com" + img_tag["src"]
        img_filename = img_url.split("/")[-1]  # 真實圖檔名稱
    else:
        img_filename = f"{pid}_{subid}.png"
        img_url = f"https://tw.portal-pokemon.com/play/resources/pokedex/img/pm_{pid}_{int(subid):02}.png"
    img_path = os.path.join(IMAGE_DIR, img_filename)

    if not os.path.exists(img_path):
        img_res = requests.get(img_url)
        if img_res.status_code == 200:
            with open(img_path, "wb") as f:
                f.write(img_res.content)
            print(f"🖼️ 圖片下載完成：{img_filename}")
        else:
            print(f"❌ 圖片下載失敗：{img_url}，狀態碼：{img_res.status_code}")
    else:
        print(f"📦 圖片已存在，略過：{img_filename}")

    entry = {
        "id": pid,
        "sub_id": int(subid),
        "name": name,
        "category": category,
        "gender": gender,
        "height": height,
        "weight": weight,
        "abilities": abilities,
        "weaknesses": weaknesses,
        "local_image_path": img_path
    }

    existing_data[key] = entry
    new_data.append(entry)
    print(f"✅ 已新增：{name} ({key})")

# 寫入結果
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(list(existing_data.values()), f, ensure_ascii=False, indent=2)

print(f"🎯 本次共新增 {len(new_data)} 筆寶可夢資料！")
driver.quit()
