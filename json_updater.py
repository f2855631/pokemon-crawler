# 匯入必要的函式庫
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

# ---------- 根據 API 回傳的子名稱與 sub_id 判斷寶可夢的型態 ----------
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
        return "normal"  # 預設型態

# ---------- 初始化 Selenium 的 Chrome Driver ----------
def init_driver():
    options = Options()
    options.add_argument("--headless")  # 不開啟瀏覽器視窗（無頭模式）
    options.add_argument("--no-sandbox")  # 跳過沙盒限制（部分環境需要）
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------- 使用 Selenium 開啟官方頁面，並用 BeautifulSoup 補抓詳細資料 ----------
def fetch_details_from_html(driver, zukan_id):
    url = f"https://tw.portal-pokemon.com/play/pokedex/{zukan_id}"
    
    # 最多重試 3 次，等待網頁載入成功
    for attempt in range(3):
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".pokemon-info__height .pokemon-info__value"))
            )
            break  # 成功載入跳出迴圈
        except Exception as e:
            print(f"⚠️ 第 {attempt+1} 次重試失敗：{zukan_id}")
            time.sleep(2)
    else:
        print(f"❌ 最終跳過 {zukan_id}，仍無法載入頁面")
        return {}

    # 使用 BeautifulSoup 解析網頁內容
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # 安全選取工具（避免標籤不存在導致程式中斷）
    def safe_select(selector):
        tag = soup.select_one(selector)
        return tag.text.strip() if tag else ""

    # 擷取基本資料
    height = safe_select(".pokemon-info__height .pokemon-info__value")
    weight = safe_select(".pokemon-info__weight .pokemon-info__value")
    category = safe_select(".pokemon-info__category .pokemon-info__value")

    # 擷取性別圖示
    gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
    gender_list = []
    for icon in gender_icons:
        src = icon.get("src", "")
        if "male" in src and "♂" not in gender_list:
            gender_list.append("♂")
        elif "female" in src and "♀" not in gender_list:
            gender_list.append("♀")
    gender = " / ".join(gender_list) if gender_list else "無"

    # 擷取特性（會移除圖片）
    ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")
    abilities = []
    for container in ability_containers:
        for img in container.find_all("img"):
            img.decompose()  # 移除 img 標籤
        text = container.get_text(strip=True)
        if text:
            abilities.append(text)

    # 擷取弱點類型
    weak_tags = soup.select(".pokemon-weakness__btn span")
    weakness = [t.text.strip() for t in weak_tags if t.text.strip()]

    # 擷取屬性類型
    type_tags = soup.select(".pokemon-type__type span")
    types = [t.text.strip() for t in type_tags if t.text.strip()]

    # 回傳所有詳細資料
    return {
        "height": height,
        "weight": weight,
        "category": category,
        "gender": gender,
        "abilities": abilities,
        "weakness": weakness,
        "types": types
    }

# ---------- 主程式執行區 ----------
def main():
    API_URL = "https://tw.portal-pokemon.com/play/pokedex/api/v1?zukan_id_from=1&zukan_id_to=1200"
    data_file = "pokemon_data.json"

    # 若檔案已存在，讀入舊資料（避免重複寫入）
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    else:
        existing_data = []

    # 建立查詢用字典（以 id_sub_id 當作 key）
    existing_dict = {f"{p['id']}_{p.get('sub_id', 0)}": p for p in existing_data}

    # 取得官方 API 的資料
    response = requests.get(API_URL)
    api_data = response.json().get("pokemons", [])

    # 啟動瀏覽器
    driver = init_driver()
    output = []
    seen_ids = {}  # 用來追蹤 sub_id 重複的情況

    # 處理每一筆寶可夢
    for item in api_data:
        pokemon_id = item.get("zukan_id")
        sub_id = item.get("zukan_sub_id", 0)
        name = item.get("pokemon_name", "").strip()
        sub_name = item.get("pokemon_sub_name", "")
        key = f"{pokemon_id}_{sub_id}"

        # 處理同編號不同型態（避免重複 sub_id）
        if key in seen_ids:
            seen_ids[key] += 1
            sub_id = seen_ids[key]
        else:
            seen_ids[key] = sub_id

        image_filename = f"{int(pokemon_id):04d}_{sub_id}.png"

        # 若資料已存在就使用，否則新增空白欄位
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

        # 判斷是否需要額外補抓詳細資料
        need_detail = False
        for field in ["height", "weight", "category", "gender", "abilities", "weakness", "types"]:
            if field not in existing_entry or not existing_entry[field]:
                need_detail = True
                break

        # 有需要就爬取 HTML 詳細內容
        if need_detail:
            html_data = fetch_details_from_html(driver, pokemon_id)
            existing_entry.update(html_data)

        output.append(existing_entry)
        print(f"✅ JSON資料完成 {key}")

    # 關閉 driver
    driver.quit()

    # 寫入 JSON 檔案
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("🎉 JSON 資料更新完成！")

# ---------- 程式進入點 ----------
if __name__ == "__main__":
    main()
