import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

PLAYER_ID = "50464"  # 이승민 KBO 선수 ID

def fetch_season_stats():
    """KBO에서 시즌 성적 가져오기"""
    url = f"https://www.koreabaseball.com/record/Player/PitcherDetail/Basic.aspx?playerId={PLAYER_ID}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # 2026 성적 테이블 파싱
        tables = soup.find_all("table")
        stats = {}
        
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 8:
                    # ERA, G, W, L, HLD, IP, SO 등 파싱
                    text = [c.get_text(strip=True) for c in cells]
                    if text and text[0] == "삼성":
                        stats = {
                            "era":     text[1] if len(text) > 1 else "-",
                            "g":       text[2] if len(text) > 2 else "-",
                            "w":       text[5] if len(text) > 5 else "0",
                            "l":       text[6] if len(text) > 6 else "0",
                            "hld":     text[8] if len(text) > 8 else "0",
                            "ip":      text[13] if len(text) > 13 else "-",
                            "so":      text[16] if len(text) > 16 else "-",
                            "whip":    text[22] if len(text) > 22 else "-",
                            "np":      text[12] if len(text) > 12 else "-",
                        }
                        break
        
        return stats
    except Exception as e:
        print(f"시즌 성적 가져오기 실패: {e}")
        return {}

def fetch_game_log():
    """KBO에서 경기별 기록 가져오기"""
    url = f"https://www.koreabaseball.com/record/Player/PitcherDetail/Game.aspx?playerId={PLAYER_ID}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    games = []
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows[1:]:  # 헤더 제외
                cells = row.find_all("td")
                if len(cells) >= 10:
                    text = [c.get_text(strip=True) for c in cells]
                    try:
                        # 날짜 파싱 (MM.DD 형식으로 변환)
                        date_str = text[0]  # 예: 05.03
                        opponent = text[1]
                        result = text[2] if text[2] else "ND"
                        ip = text[5] if len(text) > 5 else "-"
                        er = int(text[12]) if len(text) > 12 and text[12].isdigit() else 0
                        np = int(text[11]) if len(text) > 11 and text[11].isdigit() else 0
                        
                        # 이닝 분수 변환 (1 1/3 → 1⅓)
                        ip = convert_innings(ip)
                        
                        # 결과 한글 변환
                        result = convert_result(result)
                        
                        games.append({
                            "date": date_str,
                            "opponent": opponent,
                            "result": result,
                            "innings": ip,
                            "er": er,
                            "pitches": np,
                            "label": make_label(ip, er, np, result)
                        })
                    except Exception:
                        continue
        
        # 최신 경기가 위로 오도록 정렬 유지
        return games[:20]  # 최근 20경기만
    except Exception as e:
        print(f"경기 기록 가져오기 실패: {e}")
        return []

def convert_innings(ip_str):
    """이닝 변환: '1 1/3' → '1⅓', '2/3' → '⅔'"""
    ip_str = ip_str.strip()
    mapping = {
        "1/3": "⅓", "2/3": "⅔",
        "1 1/3": "1⅓", "1 2/3": "1⅔",
        "2 1/3": "2⅓", "2 2/3": "2⅔",
        "3 1/3": "3⅓", "3 2/3": "3⅔",
        "4 1/3": "4⅓", "4 2/3": "4⅔",
        "5 1/3": "5⅓", "5 2/3": "5⅔",
        "6 1/3": "6⅓", "6 2/3": "6⅔",
        "7 1/3": "7⅓", "7 2/3": "7⅔",
    }
    return mapping.get(ip_str, ip_str)

def convert_result(result):
    """결과 변환"""
    mapping = {"승": "승", "패": "패", "홀": "홀드", "홀드": "홀드", "세": "세이브", "블": "BS"}
    return mapping.get(result, "ND")

def make_label(ip, er, pitches, result):
    """경기 라벨 자동 생성"""
    # 이닝 숫자 추출
    try:
        ip_num = float(ip.replace("⅓", ".33").replace("⅔", ".67").replace("⅓", ".33"))
    except:
        ip_num = 0
    
    if result == "승" and ip_num >= 6 and er <= 3:
        return "퀄리티 스타트"
    if er == 0 and ip_num >= 1:
        return "무실점"
    if result == "홀드":
        return ""
    return ""

def format_record(w, hld, l):
    """승패 기록 포맷"""
    parts = []
    if int(w) > 0:
        parts.append(f"{w}승")
    if int(hld) > 0:
        parts.append(f"{hld}홀드")
    if int(l) > 0:
        parts.append(f"{l}패")
    return " ".join(parts) if parts else "0승"

def update_html(stats, games):
    """index.html 업데이트"""
    with open("index.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    if not stats:
        print("성적 데이터 없음, 업데이트 건너뜀")
        return
    
    # SEASON 데이터 업데이트
    record_str = format_record(
        stats.get("w", "0"),
        stats.get("hld", "0"),
        stats.get("l", "0")
    )
    
    new_season = f"""  const SEASON = {{
    era:     "{stats.get('era', '-')}",
    record:  "{record_str}",
    innings: "{stats.get('ip', '-')}",
    k:       "{stats.get('so', '-')}",
  }};"""
    
    html = re.sub(
        r'const SEASON = \{[^}]+\};',
        new_season,
        html,
        flags=re.DOTALL
    )
    
    # GAMES 데이터 업데이트
    if games:
        games_lines = []
        for g in games:
            label = g.get('label', '')
            games_lines.append(
                f'    {{ date:"{g["date"]}", opponent:"{g["opponent"]}", result:"{g["result"]}", '
                f'innings:"{g["innings"]}", er:{g["er"]}, pitches:{g["pitches"]}, label:"{label}" }},'
            )
        
        new_games = "  const GAMES = [\n" + "\n".join(games_lines) + "\n  ];"
        
        html = re.sub(
            r'const GAMES = \[[^\]]*\];',
            new_games,
            html,
            flags=re.DOTALL
        )
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✅ 업데이트 완료! ERA: {stats.get('era')}, 기록: {record_str}")

if __name__ == "__main__":
    print(f"⚾ 이승민 성적 업데이트 시작 ({datetime.now().strftime('%Y.%m.%d %H:%M')})")
    
    stats = fetch_season_stats()
    games = fetch_game_log()
    
    print(f"시즌 성적: {stats}")
    print(f"경기 기록: {len(games)}경기")
    
    update_html(stats, games)
