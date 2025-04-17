from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
import os
import requests

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

base_url = "https://tw.portal-pokemon.com/play/pokedex/"
pokemon_list = []

# 建立本地圖片資料夾
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)

# 讀取已存在的 JSON 資料（若有）
existing_ids = set()
if os.path.exists("pokemon_data.json"):
    with open("pokemon_data.json", "r", encoding="utf-8") as f:
        existing_data = json.load(f)
        existing_ids = set(p["id"] for p in existing_data)
else:
    existing_data = []

num = 1
while True:
    base_id = str(num).zfill(4)
    sub_id = 0

    while sub_id <= 3:
        pokemon_id = base_id if sub_id == 0 else f"{base_id}_{sub_id}"

        if pokemon_id in existing_ids:
            print(f"⏭️ 已存在 {pokemon_id}，略過")
            sub_id += 1
            continue

        url = base_url + pokemon_id
        print(f"🐾 正在抓取 {pokemon_id}...")

        try:
            driver.get(url)
            time.sleep(3)
            soup = BeautifulSoup(driver.page_source, "html.parser")

            page_msg = soup.select_one(".page-other__lead")
            if page_msg and "can't be found" in page_msg.text:
                # 若連主頁面都不存在，代表整體圖鑑結束，終止爬蟲流程
                    print(f"⛔ {pokemon_id} 是主體頁，終止爬蟲")
                    driver.quit()
                    all_pokemon = existing_data + pokemon_list
                    with open("pokemon_data.json", "w", encoding="utf-8") as f:
                        json.dump(all_pokemon, f, ensure_ascii=False, indent=2)
                    break  # 用 break 結束 while True 外層迴圈
                else:
                    print(f"🔚 {pokemon_id} 是延伸型態不存在，結束延伸嘗試")
                    break

            name_tag = soup.select_one(".pokemon-slider__main-name")
            if not name_tag or not name_tag.text.strip():
                print(f"⚠️ 抓不到名字或名稱為空：編號 {pokemon_id}，略過")
                sub_id += 1
                continue
            name_zh = name_tag.text.strip()

            type_tags = soup.select(".pokemon-type__type")
            type_list = [t.text.strip() for t in type_tags]

            height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
            weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")
            height = height_tag.text.strip() if height_tag else ""
            weight = weight_tag.text.strip() if weight_tag else ""

            img_tag = soup.select_one(".pokemon-img__front")
            img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else ""
            if img_url.startswith("/"):
                img_url = "https://tw.portal-pokemon.com" + img_url

            img_filename = f"{pokemon_id}_{name_zh}.png"
            img_path = os.path.join(image_dir, img_filename)
            if img_url:
                try:
                    response = requests.get(img_url, timeout=10)
                    if response.status_code == 200:
                        with open(img_path, "wb") as img_file:
                            img_file.write(response.content)
                except Exception as img_err:
                    print(f"⚠️ 圖片下載失敗：{img_err}")
                    img_path = ""

            weak_tags = soup.select(".pokemon-weakness__btn span")
            weak_list = [t.text.strip() for t in weak_tags if t.text.strip()]

            category_tag = soup.select_one(".pokemon-info__category .pokemon-info__value")
            category = category_tag.text.strip() if category_tag else ""

            gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
            gender_list = []
            for icon in gender_icons:
                src = icon.get("src", "")
                if "male" in src and "公" not in gender_list:
                    gender_list.append("公")
                elif "female" in src and "母" not in gender_list:
                    gender_list.append("母")
            gender = " / ".join(gender_list) if gender_list else "無"

            ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")
            abilities = []
            for container in ability_containers:
                for img in container.find_all("img"):
                    img.decompose()
                ability_text = container.get_text(strip=True)
                if ability_text:
                    abilities.append(ability_text)

            pokemon = {
                "id": pokemon_id,
                "name": name_zh,
                "types": type_list,
                "height": height,
                "weight": weight,
                "image": img_path,
                "weakness": weak_list,
                "category": category,
                "gender": gender,
                "abilities": abilities
            }

            pokemon_list.append(pokemon)
            print(f"✅ 已抓取 {name_zh} ✅")
            sub_id += 1

        except Exception as e:
            print(f"❌ 發生錯誤：{e}")
            break

    num += 1

driver.quit()

# 合併原本資料 + 新資料後存檔
all_pokemon = existing_data + pokemon_list
with open("pokemon_data.json", "w", encoding="utf-8") as f:
    json.dump(all_pokemon, f, ensure_ascii=False, indent=2)
