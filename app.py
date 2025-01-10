# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import requests
from collections import defaultdict
import time  # timeモジュールをインポート

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッションを使用するために必要

# リージョンマッピング (プラットフォーム用 & リージョナル用)
REGION_MAPPING = {
    "na1": {
        "platform": "na1.api.riotgames.com",
        "regional": "americas.api.riotgames.com"
    },
    "br1": {
        "platform": "br1.api.riotgames.com",
        "regional": "americas.api.riotgames.com"
    },
    "la1": {
        "platform": "la1.api.riotgames.com",
        "regional": "americas.api.riotgames.com"
    },
    "la2": {
        "platform": "la2.api.riotgames.com",
        "regional": "americas.api.riotgames.com"
    },
    "euw1": {
        "platform": "euw1.api.riotgames.com",
        "regional": "europe.api.riotgames.com"
    },
    "eun1": {
        "platform": "eun1.api.riotgames.com",
        "regional": "europe.api.riotgames.com"
    },
    "tr1": {
        "platform": "tr1.api.riotgames.com",
        "regional": "europe.api.riotgames.com"
    },
    "ru": {
        "platform": "ru.api.riotgames.com",
        "regional": "europe.api.riotgames.com"
    },
    "me1": {
        "platform": "me1.api.riotgames.com",
        "regional": "europe.api.riotgames.com"
    },
    "jp1": {
        "platform": "jp1.api.riotgames.com",
        "regional": "asia.api.riotgames.com"
    },
    "kr": {
        "platform": "kr.api.riotgames.com",
        "regional": "asia.api.riotgames.com"
    },
    "oc1": {
        "platform": "oc1.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    },
    "ph2": {
        "platform": "ph2.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    },
    "sg2": {
        "platform": "sg2.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    },
    "th2": {
        "platform": "th2.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    },
    "tw2": {
        "platform": "tw2.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    },
    "vn2": {
        "platform": "vn2.api.riotgames.com",
        "regional": "sea.api.riotgames.com"
    }
}


def get_player_data(riot_id, tagline, region, api_key):
    """
    region をキーに、REGION_MAPPING から
      platform_domain, regional_domain
    を取得して、APIリクエストを切り替える
    """
    puuid = None
    profile_icon_url = None
    summoner_level = None
    summoner_id = None
    summoner_name = None
    match_ids = []
    match_details = []
    average_stats = defaultdict(lambda: {
        'gold': 0,
        'xp': 0,
        'minionsKilled': 0,
        'jungleMinionsKilled': 0,
        'damage': 0,
        'championKills': 0,
        'championDeaths': 0,
        'championAssists': 0,
        'level': 0
    })
    error = None
    rank_info = []

    def make_request_with_retry(url):
        """429エラーが発生した場合にリトライする関数"""
        while True:
            response = requests.get(url)
            if response.status_code == 429:
                print("429エラー: リクエストが多すぎます。2分1秒待機します。")
                time.sleep(121)
            else:
                return response

    # リージョンが無効値の場合
    if region not in REGION_MAPPING:
        return {
            'error': f"無効なリージョン {region} が選択されています。",
            'puuid': None,
            'profile_icon_url': None,
            'summoner_level': None,
            'summoner_id': None,
            'summoner_name': None,
            'match_ids': [],
            'match_details': [],
            'average_stats': {},
            'rank_info': []
        }

    platform_domain = REGION_MAPPING[region]['platform']   # Summoner-V4, League-V4
    regional_domain = REGION_MAPPING[region]['regional']   # Match-V5, etc.

    # ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
    # Account-V1だけ別ドメインへ差し替えるロジックを入れる
    # "oc1", "ph2", "sg2", "th2", "tw2", "vn2" の場合
    # regionがseaになってしまうが、Account-V1は使用できない
    # → "europe.api.riotgames.com" に差し替える

    account_domain = regional_domain  # 初期値は同じ
    # sea→europe への差し替え対象
    sea_regions = {"oc1", "ph2", "sg2", "th2", "tw2", "vn2"}
    if region in sea_regions and regional_domain == "sea.api.riotgames.com":
        # Account-V1に限っては sea -> europe に差し替える
        account_domain = "europe.api.riotgames.com"
    # ↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑↑

    if not riot_id or not tagline:
        error = 'Riot IDとタグラインを入力してください。'
    else:
        # Account-V1: リージョナルルート  (→ ここを account_domain で置き換える)
        url_account = f"https://{account_domain}/riot/account/v1/accounts/by-riot-id/{riot_id}/{tagline}?api_key={api_key}"
        response = make_request_with_retry(url_account)
        if response.status_code == 200:
            data = response.json()
            puuid = data.get('puuid')
            if not puuid:
                error = 'puuidが取得できませんでした。'
            else:
                # Summoner-V4: プラットフォームルート
                summoner_url = f"https://{platform_domain}/lol/summoner/v4/summoners/by-puuid/{puuid}?api_key={api_key}"
                summoner_response = make_request_with_retry(summoner_url)
                if summoner_response.status_code == 200:
                    summoner_data = summoner_response.json()
                    profile_icon_id = summoner_data.get('profileIconId')
                    summoner_level = summoner_data.get('summonerLevel')
                    summoner_id = summoner_data.get('id')
                    summoner_name = summoner_data.get('name')
                    if profile_icon_id:
                        # 14.24.1 などバージョンは随時更新
                        profile_icon_url = f"http://ddragon.leagueoflegends.com/cdn/14.24.1/img/profileicon/{profile_icon_id}.png"

                    # リーグ情報 (League-V4): プラットフォームルート
                    league_url = f"https://{platform_domain}/lol/league/v4/entries/by-summoner/{summoner_id}?api_key={api_key}"
                    league_response = make_request_with_retry(league_url)
                    if league_response.status_code == 200:
                        leagues = league_response.json()
                        for league in leagues:
                            queue_type = league.get('queueType')
                            tier = league.get('tier')
                            rank = league.get('rank')
                            league_points = league.get('leaguePoints')
                            wins = league.get('wins')
                            losses = league.get('losses')
                            rank_info.append({
                                'queueType': queue_type,
                                'tier': tier,
                                'rank': rank,
                                'leaguePoints': league_points,
                                'wins': wins,
                                'losses': losses
                            })
                    else:
                        error = f"ランク情報の取得に失敗しました。ステータスコード: {league_response.status_code}, レスポンス: {league_response.text}"

                    # Match-V5: リージョナルルート (ここは sea のままでOK)
                    match_url = f"https://{regional_domain}/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count=20&api_key={api_key}"
                    match_response = make_request_with_retry(match_url)
                    if match_response.status_code == 200:
                        match_ids = match_response.json()
                        for match_id in match_ids:
                            match_url_detail = f"https://{regional_domain}/lol/match/v5/matches/{match_id}?api_key={api_key}"
                            match_info_response = make_request_with_retry(match_url_detail)
                            if match_info_response.status_code == 200:
                                match_info = match_info_response.json()
                                game_duration = match_info['info'].get('gameDuration', 0)
                                if game_duration < 1200:
                                    continue

                                game_type = match_info['info']['gameMode']
                                queue_type_num = match_info['info']['queueId']

                                if game_type == "CLASSIC" and queue_type_num == 420:
                                    if queue_type_num == 420:
                                        queue_type_str = "ソロ"
                                    elif queue_type_num == 440:
                                        queue_type_str = "フレックス"
                                    else:
                                        queue_type_str = "その他"

                                    teams = match_info['info']['teams']
                                    participant_team_id = None
                                    for participant in match_info['info']['participants']:
                                        if participant['puuid'] == puuid:
                                            participant_team_id = participant['teamId']
                                            break
                                    if participant_team_id is None:
                                        win = "不明"
                                    else:
                                        win = "勝利" if any(t['teamId'] == participant_team_id and t['win'] for t in teams) else "敗北"

                                    champion_url = "http://ddragon.leagueoflegends.com/cdn/14.24.1/data/ja_JP/champion.json"
                                    champion_response = make_request_with_retry(champion_url)
                                    if champion_response.status_code == 200:
                                        champions_data = champion_response.json()
                                        # { '1': 'Annie', ... }
                                        champions = {champion['key']: champion['id'] for champion in champions_data['data'].values()}
                                    else:
                                        error = f"チャンピオン情報の取得に失敗しました。ステータスコード: {champion_response.status_code}, レスポンス: {champion_response.text}"
                                        continue

                                    participant_obj = next((p for p in match_info['info']['participants'] if p['puuid'] == puuid), None)
                                    if not participant_obj:
                                        continue

                                    summoner_name_match = participant_obj['summonerName']
                                    champion_id = participant_obj['championId']
                                    champion_name = champions.get(str(champion_id), "不明")
                                    champion_icon_url = f"http://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/{champion_name}.png"
                                    participant_id_num = participant_obj['participantId']

                                    timeline_url = f"https://{regional_domain}/lol/match/v5/matches/{match_id}/timeline?api_key={api_key}"
                                    timeline_response = make_request_with_retry(timeline_url)
                                    if timeline_response.status_code == 200:
                                        timeline_data = timeline_response.json()
                                        frames = timeline_data['info']['frames']

                                        gold_over_time = []
                                        xp_over_time = []
                                        minions_killed_over_time = []
                                        jungle_minions_killed_over_time = []
                                        damage_over_time = []
                                        champion_kills_over_time = []
                                        champion_deaths_over_time = []
                                        champion_assists_over_time = []
                                        level_over_time = []
                                        max_time_slot = 0

                                        current_total_champion_kills = 0
                                        current_total_champion_deaths = 0
                                        current_total_champion_assists = 0

                                        events_by_time = {}
                                        for frame in frames:
                                            timestamp = frame['timestamp'] // 1000
                                            time_slot = (timestamp // 60) * 60
                                            if time_slot not in events_by_time:
                                                events_by_time[time_slot] = []
                                            events_by_time[time_slot].extend(frame.get('events', []))
                                            if time_slot > max_time_slot:
                                                max_time_slot = time_slot

                                        for ts in range(0, max_time_slot + 60, 60):
                                            events = events_by_time.get(ts, [])
                                            for event in events:
                                                if event.get('type') == 'CHAMPION_KILL':
                                                    killer = event.get('killerId')
                                                    victim = event.get('victimId')
                                                    assisting_participants = event.get('assistingParticipantIds', [])
                                                    if killer == participant_id_num:
                                                        current_total_champion_kills += 1
                                                    if victim == participant_id_num:
                                                        current_total_champion_deaths += 1
                                                    if participant_id_num in assisting_participants:
                                                        current_total_champion_assists += 1
                                            champion_kills_over_time.append({'time': ts, 'championKills': current_total_champion_kills})
                                            champion_deaths_over_time.append({'time': ts, 'championDeaths': current_total_champion_deaths})
                                            champion_assists_over_time.append({'time': ts, 'championAssists': current_total_champion_assists})

                                        for frame in frames:
                                            timestamp = frame['timestamp'] // 1000
                                            time_slot = (timestamp // 60) * 60
                                            participant_frame = frame['participantFrames'].get(str(participant_id_num), {})
                                            if participant_frame:
                                                total_gold = participant_frame.get('totalGold', 0)
                                                if not gold_over_time or gold_over_time[-1]['time'] != time_slot:
                                                    gold_over_time.append({'time': time_slot, 'gold': total_gold})
                                                else:
                                                    gold_over_time[-1]['gold'] = total_gold

                                                total_xp = participant_frame.get('xp', 0)
                                                if not xp_over_time or xp_over_time[-1]['time'] != time_slot:
                                                    xp_over_time.append({'time': time_slot, 'xp': total_xp})
                                                else:
                                                    xp_over_time[-1]['xp'] = total_xp

                                                minions_killed = participant_frame.get('minionsKilled', 0)
                                                if not minions_killed_over_time or minions_killed_over_time[-1]['time'] != time_slot:
                                                    minions_killed_over_time.append({'time': time_slot, 'minionsKilled': minions_killed})
                                                else:
                                                    minions_killed_over_time[-1]['minionsKilled'] = minions_killed

                                                jungle_minions_killed = participant_frame.get('jungleMinionsKilled', 0)
                                                if not jungle_minions_killed_over_time or jungle_minions_killed_over_time[-1]['time'] != time_slot:
                                                    jungle_minions_killed_over_time.append({'time': time_slot, 'jungleMinionsKilled': jungle_minions_killed})
                                                else:
                                                    jungle_minions_killed_over_time[-1]['jungleMinionsKilled'] = jungle_minions_killed

                                                total_damage = participant_frame.get('damageStats', {}).get('totalDamageDoneToChampions', 0)
                                                if not damage_over_time or damage_over_time[-1]['time'] != time_slot:
                                                    damage_over_time.append({'time': time_slot, 'damage': total_damage})
                                                else:
                                                    damage_over_time[-1]['damage'] = total_damage

                                                current_level = participant_frame.get('level', 1)
                                                if not level_over_time or level_over_time[-1]['time'] != time_slot:
                                                    level_over_time.append({'time': time_slot, 'level': current_level})
                                                else:
                                                    level_over_time[-1]['level'] = current_level

                                        match_details.append({
                                            'match_id': match_id,
                                            'summoner_name': summoner_name_match,
                                            'champion_name': champion_name,
                                            'champion_icon_url': champion_icon_url,
                                            'participant_id': participant_id_num,
                                            'game_type': game_type,
                                            'queue_type': queue_type_str,
                                            'win': win,
                                            'level_over_time': level_over_time,
                                            'gold_over_time': gold_over_time,
                                            'xp_over_time': xp_over_time,
                                            'minions_killed_over_time': minions_killed_over_time,
                                            'jungle_minions_killed_over_time': jungle_minions_killed_over_time,
                                            'damage_over_time': damage_over_time,
                                            'champion_kills_over_time': sorted(champion_kills_over_time, key=lambda x: x['time']),
                                            'champion_deaths_over_time': sorted(champion_deaths_over_time, key=lambda x: x['time']),
                                            'champion_assists_over_time': sorted(champion_assists_over_time, key=lambda x: x['time'])
                                        })
                                    else:
                                        error = f"タイムライン情報の取得に失敗しました。ステータスコード: {timeline_response.status_code}, レスポンス: {timeline_response.text}"
                            else:
                                error = f"試合情報の取得に失敗しました。ステータスコード: {match_info_response.status_code}, レスポンス: {match_info_response.text}"
                    else:
                        error = f"試合情報の取得に失敗しました。ステータスコード: {match_response.status_code}, レスポンス: {match_response.text}"
                else:
                    error = f"サモナー情報の取得に失敗しました。ステータスコード: {summoner_response.status_code}, レスポンス: {summoner_response.text}"
        elif response.status_code == 404:
            error = 'アカウントが見つかりませんでした。'
        else:
            error = f"エラーが発生しました。ステータスコード: {response.status_code}, レスポンス: {response.text}"

        # 平均ステータス
        if match_details:
            for match in match_details:
                for stat in [
                    'gold_over_time',
                    'xp_over_time',
                    'minions_killed_over_time',
                    'jungle_minions_killed_over_time',
                    'damage_over_time',
                    'champion_kills_over_time',
                    'champion_deaths_over_time',
                    'champion_assists_over_time',
                    'level_over_time'
                ]:
                    for entry in match.get(stat, []):
                        t = entry['time']
                        if stat == 'gold_over_time':
                            average_stats[t]['gold'] += entry['gold']
                        elif stat == 'xp_over_time':
                            average_stats[t]['xp'] += entry['xp']
                        elif stat == 'minions_killed_over_time':
                            average_stats[t]['minionsKilled'] += entry['minionsKilled']
                        elif stat == 'jungle_minions_killed_over_time':
                            average_stats[t]['jungleMinionsKilled'] += entry['jungleMinionsKilled']
                        elif stat == 'damage_over_time':
                            average_stats[t]['damage'] += entry['damage']
                        elif stat == 'champion_kills_over_time':
                            average_stats[t]['championKills'] += entry['championKills']
                        elif stat == 'champion_deaths_over_time':
                            average_stats[t]['championDeaths'] += entry['championDeaths']
                        elif stat == 'champion_assists_over_time':
                            average_stats[t]['championAssists'] += entry['championAssists']
                        elif stat == 'level_over_time':
                            average_stats[t]['level'] += entry['level']

            time_counts = defaultdict(int)
            for match in match_details:
                times = [e['time'] for e in match.get('gold_over_time', [])]
                for t in times:
                    time_counts[t] += 1

            for t, stats in average_stats.items():
                count = time_counts.get(t, 1)
                stats['gold'] /= count
                stats['xp'] /= count
                stats['minionsKilled'] /= count
                stats['jungleMinionsKilled'] /= count
                stats['damage'] /= count
                stats['championKills'] /= count
                stats['championDeaths'] /= count
                stats['championAssists'] /= count
                stats['level'] /= count

            average_stats = dict(sorted(average_stats.items()))

    return {
        'puuid': puuid,
        'profile_icon_url': profile_icon_url,
        'summoner_level': summoner_level,
        'summoner_id': summoner_id,
        'summoner_name': summoner_name,
        'match_ids': match_ids,
        'match_details': match_details,
        'average_stats': average_stats,
        'rank_info': rank_info,
        'error': error
    }


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'riot' and password == 'develop':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Invalid ID or Password'
    return render_template('login.html', error=error)


@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    players = []
    error = None

    riot_id1 = None
    tagline1 = None
    region1 = None

    riot_id2 = None
    tagline2 = None
    region2 = None

    if request.method == 'POST':
        # フォームからAPIキーを取得
        api_key = request.form.get('api_key')

        riot_id1 = request.form.get('riot_id1')
        tagline1 = request.form.get('tagline1')
        region1 = request.form.get('region1')

        riot_id2 = request.form.get('riot_id2')
        tagline2 = request.form.get('tagline2')
        region2 = request.form.get('region2')

        # プレイヤー1のデータ取得
        player1 = get_player_data(riot_id1, tagline1, region1, api_key)
        players.append(player1)

        # プレイヤー2のデータ取得
        player2 = get_player_data(riot_id2, tagline2, region2, api_key)
        players.append(player2)

        # エラーメッセージの集約
        errors = [p['error'] for p in players if p['error']]
        if errors:
            error = ' '.join(errors)

    return render_template(
        'index.html',
        players=players if players else None,
        error=error,
        riot_id1=riot_id1,
        riot_id2=riot_id2
    )


if __name__ == '__main__':
    app.run(debug=True)
