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

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

base_url = "https://tw.portal-pokemon.com/play/pokedex/"
pokemon_list = []

for num in range(1, 1026):  # 可調整抓取範圍
    pokemon_id = str(num).zfill(4)
    url = base_url + pokemon_id

    print(f"🐾 正在抓取 {pokemon_id}...")

    driver.get(url)
    time.sleep(3)  # 增加等待時間確保頁面載入完成

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".pokemon-slider__main-name"))
        )

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 名稱
        name_tag = soup.select_one(".pokemon-slider__main-name")
        if not name_tag:
            print(f"⚠️ 抓不到名字：編號 {pokemon_id}")
            continue
        name_zh = name_tag.text.strip()

        # 屬性
        type_tags = soup.select(".pokemon-type__type")
        type_list = [t.text.strip() for t in type_tags]

        # 身高 / 體重
        height_tag = soup.select_one(".pokemon-info__height .pokemon-info__value")
        weight_tag = soup.select_one(".pokemon-info__weight .pokemon-info__value")
        height = height_tag.text.strip() if height_tag else ""
        weight = weight_tag.text.strip() if weight_tag else ""

        # 圖片
        img_tag = soup.select_one(".pokemon-img__front")
        img_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else ""
        if img_url.startswith("/"):
            img_url = "https://tw.portal-pokemon.com" + img_url

        # 弱點
        weak_tags = soup.select(".pokemon-weakness__btn span")
        weak_list = [t.text.strip() for t in weak_tags if t.text.strip()]

        # 分類
        category_tag = soup.select_one(".pokemon-info__category .pokemon-info__value")
        category = category_tag.text.strip() if category_tag else ""

        # 性別
        # 依據抓取到的性別圖示進行處理
        gender_icons = soup.select(".pokemon-info__gender .pokemon-info__gender-icon")
        gender_list = []
        
        for icon in gender_icons:
            src = icon.get("src", "")
            
            # 確保有 src 且 src 中包含 "male" 或 "female"
            if "male" in src and "公" not in gender_list:
                gender_list.append("公")
            elif "female" in src and "母" not in gender_list:
                gender_list.append("母")
        
        # 如果有性別圖示，顯示對應性別；如果沒有則顯示 "無"
        gender = " / ".join(gender_list) if gender_list else "無"

        # 特性名稱：抓取連結
        ability_containers = soup.select(".pokemon-info__abilities .pokemon-info__value.size-14")

        abilities = []
        for container in ability_containers:
            # 去除圖片
            for img in container.find_all("img"):
                img.decompose()
        
            ability_text = container.get_text(strip=True)
            if ability_text:
                abilities.append(ability_text)
        
        # 如果沒有找到任何特性，則將 abilities 設為空列表
        if not abilities:
            abilities = []

        # 整理資料
        pokemon = {
            "id": pokemon_id,
            "name": name_zh,
            "types": type_list,
            "height": height,
            "weight": weight,
            "image": img_url,
            "weakness": weak_list,
            "category": category,
            "gender": gender,
            "abilities": abilities            
        }

        pokemon_list.append(pokemon)
        print(f"✅ 已抓取 {name_zh} ✅")

    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        continue

driver.quit()

# 存檔
with open("pokemon_data.json", "w", encoding="utf-8") as f:
    json.dump(pokemon_list, f, ensure_ascii=False, indent=2)
