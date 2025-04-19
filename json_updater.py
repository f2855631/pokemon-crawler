import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?pokemon_ability_id=&zukan_id_from=1&zukan_id_to=1200"
data_file = "pokemon_data.json"

if os.path.exists(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        existing_data = json.load(f)
else:
    existing_data = []

existing_dict = {f"{p['id']}_{p.get('sub_id', 0)}": p for p in existing_data}

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

response = requests.get(API_URL)
try:
    json_data = response.json()
    api_data = json_data.get("pokemons", [])
except Exception as e:
    print("❌ API 回傳錯誤：", e)
    driver.quit()
    exit(1)

updated_data = []

for entry in api_data:
    pokemon_id = entry.get("zukan_id")
    sub_id = entry.get("zukan_sub_id", 0)
    name = entry.get("pokemon_name")
    key = f"{pokemon_id}_{sub_id}"

    if key in existing_dict:
        existing_entry = existing_dict[key]
    else:
        existing_entry = {"id": pokemon_id, "sub_id": sub_id, "name": name}

    need_detail = False
    for field in ["height", "weight", "category", "gender", "abilities", "weakness"]:
        if field not in existing_entry or not existing_entry[field]:
            need_detail = True
            break

    if not need_detail and existing_entry.get("gender", "") in ["公", "母", "公 / 母", "母 / 公"]:
        print(f"🔁 性別欄位格式需更新：{key}")
        need_detail = True

    if need_detail:
        url = f"https://tw.portal-pokemon.com/play/pokedex/{pokemon_id}"
        try:
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "pokemon-info__height"))
            )
        except Exception as e:
            print(f"❌ 跳過 {key}，無法載入頁面：{e}")
            continue

        soup = BeautifulSoup(driver.page_source, "html.parser")

        height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
        weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")
        existing_entry["height"] = height_tag.text.strip() if height_tag else ""
        existing_entry["weight"] = weight_tag.text.strip() if weight_tag else ""

        category_tag = soup.select_one(".pokemon-info__category .pokemon-info__value")
        existing_entry["category"] = category_tag.text.strip() if category_tag else ""

        gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
        gender_list = []
        for icon in gender_icons:
            src = icon.get("src", "")
            if "male" in src and "♂" not in gender_list:
                gender_list.append("♂")
            elif "female" in src and "♀" not in gender_list:
                gender_list.append("♀")
        existing_entry["gender"] = " / ".join(gender_list) if gender_list else "無"

        ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")
        abilities = []
        for container in ability_containers:
            for img in container.find_all("img"):
                img.decompose()
            text = container.get_text(strip=True)
            if text:
                abilities.append(text)
        existing_entry["abilities"] = abilities

        weak_tags = soup.select(".pokemon-weakness__btn span")
        existing_entry["weakness"] = [t.text.strip() for t in weak_tags if t.text.strip()]

        # 直接從 HTML 補抓 types，不再依賴 API
        type_tags = soup.select(".pokemon-type__type span")
        existing_entry["types"] = [t.text.strip() for t in type_tags if t.text.strip()]

    updated_data.append(existing_entry)
    print(f"✅ JSON資料完成 {key}")

driver.quit()

with open(data_file, "w", encoding="utf-8") as f:
    json.dump(updated_data, f, ensure_ascii=False, indent=2)

print("🎉 JSON 資料更新完成！")
