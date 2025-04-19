import os
import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# ================== 初始化 ==================
API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from=1&zukan_id_to=1200"
data_file = "pokemon_data.json"
image_dir = "images"
os.makedirs(image_dir, exist_ok=True)

# 載入現有資料
if os.path.exists(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
else:
    existing_data = []

existing_dict = {f"{p['id']}_{p.get('sub_id', 0)}": p for p in existing_data}

# ================== 設定 Selenium ==================
options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ================== 從 API 抓基本資料 ==================
response = requests.get(API_URL)
try:
    api_data = response.json()
    if not isinstance(api_data, list):
        raise ValueError("API response is not a list")
except Exception as e:
    print("❌ 無法解析 API JSON，錯誤內容：", e)
    print("原始回應內容：", response.text[:200])
    driver.quit()
    exit(1)

updated_data = []

for entry in api_data:
    print("\n➡️ API entry:", entry)
    print("📌 type:", type(entry))

    if not isinstance(entry, dict):
        print("⚠️ 跳過不合法資料項：不是 dict")
        continue

    pokemon_id = entry.get("id")
    sub_id = entry.get("sub_id", 0)
    name = entry.get("name")
    types = entry.get("type", [])
    key = f"{pokemon_id}_{sub_id}"

    if key in existing_dict:
        existing_entry = existing_dict[key]
    else:
        existing_entry = {"id": pokemon_id, "sub_id": sub_id, "name": name, "types": types}

    # 是否需要抓取細節？（缺欄位或圖片不存在）
    need_detail = False
    for field in ["height", "weight", "category", "gender", "abilities", "weakness"]:
        if field not in existing_entry or not existing_entry[field]:
            need_detail = True
            break

    image_filename = f"{pokemon_id}_{name}.png"
    image_path = os.path.join(image_dir, image_filename)
    if not os.path.exists(image_path):
        need_detail = True

    if need_detail:
        print(f"🐾 抓取細節 {key}...")
        url = f"https://tw.portal-pokemon.com/play/pokedex/{pokemon_id}"
        driver.get(url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Height & Weight
        height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
        weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")
        existing_entry["height"] = height_tag.text.strip() if height_tag else ""
        existing_entry["weight"] = weight_tag.text.strip() if weight_tag else ""

        # Category
        category_tag = soup.select_one(".pokemon-info__category .pokemon-info__value")
        existing_entry["category"] = category_tag.text.strip() if category_tag else ""

        # Gender
        gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
        gender_list = []
        for icon in gender_icons:
            src = icon.get("src", "")
            if "male" in src:
                gender_list.append("公")
            elif "female" in src:
                gender_list.append("母")
        existing_entry["gender"] = " / ".join(gender_list) if gender_list else "無"

        # Abilities
        ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")
        abilities = []
        for container in ability_containers:
            for img in container.find_all("img"):
                img.decompose()
            ability_text = container.get_text(strip=True)
            if ability_text:
                abilities.append(ability_text)
        existing_entry["abilities"] = abilities

        # Weakness
        weak_tags = soup.select(".pokemon-weakness__btn span")
        existing_entry["weakness"] = [t.text.strip() for t in weak_tags if t.text.strip()]

        # Image
        img_tag = soup.select_one(".pokemon-img__front")
        img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else ""
        if img_url.startswith("/"):
            img_url = "https://tw.portal-pokemon.com" + img_url

        if img_url:
            try:
                img_response = requests.get(img_url, timeout=10)
                if img_response.status_code == 200:
                    with open(image_path, "wb") as img_file:
                        img_file.write(img_response.content)
                    existing_entry["image"] = image_path
                else:
                    print(f"⚠️ 圖片下載失敗 {key}：狀態碼 {img_response.status_code}")
            except Exception as e:
                print(f"⚠️ 圖片下載錯誤 {key}：{e}")
        else:
            print(f"⚠️ 沒有圖片 URL：{key}")

    updated_data.append(existing_entry)
    print(f"✅ 處理完成 {key}")

# 關閉瀏覽器
driver.quit()

# 儲存新資料
with open(data_file, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print("🎉 所有寶可夢資料更新完成！")

