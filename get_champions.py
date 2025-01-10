import requests
import json

# ddragonのチャンピオンデータのURL
champions_url = "http://ddragon.leagueoflegends.com/cdn/14.24.1/data/ja_JP/champion.json"

# チャンピオンデータを取得
response = requests.get(champions_url)

if response.status_code == 200:
    champions_data = response.json()
    champions_list = {
        champion['key']: {
            'name': champion['name'],  # 日本語名
            'id': champion['id']        # 英語チャンピオン名
        } for champion in champions_data['data'].values()
    }

    # JSONファイルに保存
    with open('champions.json', 'w', encoding='utf-8') as f:
        json.dump(champions_list, f, ensure_ascii=False, indent=4)
    print("チャンピオンキーを元に、名前（日本語）とID（英語チャンピオン名）を champions.json に保存しました。")
else:
    print(f"チャンピオンデータの取得に失敗しました。ステータスコード: {response.status_code}")
