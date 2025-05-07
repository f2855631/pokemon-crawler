import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# ---------- form_type 判斷邏輯（改為僅靠 API） ----------
def infer_form_type_api(sub_name: str, sub_id: int) -> str:
    if "阿羅拉" in sub_name:
        return "alola"
    elif "伽勒爾" in sub_name:
        return "galar"
    elif "洗翠" in sub_name:
        return "hisui"
    elif "帕底亞" in sub_name:
        return "paldea"
    elif "超極巨化" in sub_name:
        return "gmax"
    elif sub_name == "" and sub_id > 0:
        return "mega"
    else:
        return "normal"

# ---------- 啟動 Selenium ----------
def init_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------- HTML 補抓細節資料 ----------
def fetch_details_from_html(driver, zukan_id):
    url = f"https://tw.portal-pokemon.com/play/pokedex/{zukan_id}"
    for attempt in range(3):
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pokemon-info__height .pokemon-info__value"))
            )
            break
        except Exception as e:
            print(f"⚠️ 第 {attempt+1} 次重試失敗：{zukan_id}")
            time.sleep(2)
    else:
        print(f"❌ 最終跳過 {zukan_id}，仍無法載入頁面")
        return {}

    soup = BeautifulSoup(driver.page_source, "html.parser")

    def safe_select(selector):
        tag = soup.select_one(selector)
        return tag.text.strip() if tag else ""

    height = safe_select(".pokemon-info__height .pokemon-info__value")
    weight = safe_select(".pokemon-info__weight .pokemon-info__value")
    category = safe_select(".pokemon-info__category .pokemon-info__value")

    gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
    gender_list = []
    for icon in gender_icons:
        src = icon.get("src", "")
        if "male" in src and "♂" not in gender_list:
            gender_list.append("♂")
        elif "female" in src and "♀" not in gender_list:
            gender_list.append("♀")
    gender = " / ".join(gender_list) if gender_list else "無"

    ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")
    abilities = []
    for container in ability_containers:
        for img in container.find_all("img"):
            img.decompose()
        text = container.get_text(strip=True)
        if text:
            abilities.append(text)

    weak_tags = soup.select(".pokemon-weakness__btn span")
    weakness = [t.text.strip() for t in weak_tags if t.text.strip()]

    type_tags = soup.select(".pokemon-type__type span")
    types = [t.text.strip() for t in type_tags if t.text.strip()]

    return {
        "height": height,
        "weight": weight,
        "category": category,
        "gender": gender,
        "abilities": abilities,
        "weakness": weakness,
        "types": types
    }

# ---------- 主爬蟲 ----------
def main():
    API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?zukan_id_from=1&zukan_id_to=1200"
    data_file = "pokemon_data.json"

    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    existing_dict = {f"{p['id']}_{p.get('sub_id', 0)}": p for p in existing_data}
    response = requests.get(API_URL)
    api_data = response.json().get("pokemons", [])

    driver = init_driver()
    output = []
    seen_ids = {}

    for item in api_data:
        pokemon_id = item.get("zukan_id")
        sub_id = item.get("zukan_sub_id", 0)
        name = item.get("pokemon_name", "").strip()
        sub_name = item.get("pokemon_sub_name", "")
        key = f"{pokemon_id}_{sub_id}"

        if key in seen_ids:
            seen_ids[key] += 1
            sub_id = seen_ids[key]
        else:
            seen_ids[key] = sub_id

        image_filename = f"{int(pokemon_id):04d}_{sub_id}.png"

        if key in existing_dict:
            existing_entry = existing_dict[key]
        else:
            existing_entry = {
                "id": pokemon_id,
                "sub_id": sub_id,
                "name": name,
                "form_name": sub_name,
                "form_type": infer_form_type_api(sub_name, sub_id),
                "image": f"images/{image_filename}"
            }

        need_detail = False
        for field in ["height", "weight", "category", "gender", "abilities", "weakness", "types"]:
            if field not in existing_entry or not existing_entry[field]:
                need_detail = True
                break

        if need_detail:
            html_data = fetch_details_from_html(driver, pokemon_id)
            existing_entry.update(html_data)

        output.append(existing_entry)
        print(f"✅ JSON資料完成 {key}")

    driver.quit()

    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("🎉 JSON 資料更新完成！")

if __name__ == "__main__":
    main()
