import json

with open("pokedex.json", "r", encoding="utf-8") as f:
    data = json.load(f)
fields = ["id", "name", "types", "height", "weight", "image", "weakness", "skills", "evolutions"]

for p in data:
    for field in fields:
        if not p.get(field):
            print(f"⚠️ 編號 {p['id']} 缺少欄位：{field}")

