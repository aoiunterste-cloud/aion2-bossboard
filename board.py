# ミスランテイダ天族のボス時間を Discord の 1 つのメッセージに書き換え続ける（GitHub Actions から 5 分おき）
# データ: Aion2 Timers の討伐報告（推定）
import json, os, time, urllib.request, datetime as dt

FEED = 'https://www.aion2timers.com/api/fieldboss.php?action=feed&server=jp-meslamtaeda'
BOSSES = [('elyos22', 'カシャパ'), ('elyos21', 'タルタン'), ('elyos24', 'ガルトゥア'), ('elyos23', 'ラグタ')]
WINDOW = 10 * 60                      # 予定時刻から湧くまでの幅（Aion2 Timers の値）
JST = dt.timezone(dt.timedelta(hours=9))
ABYSS = [('abyss02', '精霊王アグロ')]   # シエルの右翼

def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'aion2-bossboard'}), timeout=30))

def boss_line(name, k, now):
    """1 体を 1 行に: 名前・時刻・あと何分"""
    if not k:
        return f'### {name}　情報なし'
    if k.get('st') == 'up':
        hp = f"（HP {k['hp'][0]}%）" if k.get('hp') else ''
        return f'### 🔴 {name}　出現中{hp}'
    ns = int(k.get('ns') or 0)
    if not ns:
        return f'### {name}　情報なし'
    if ns <= now:
        return f'### 🟡 {name}　まもなく（<t:{ns + WINDOW}:t> ごろまで）'
    mark = '🟠 ' if ns - now <= 3600 else ''
    return f'### {mark}{name}　<t:{ns}:t>　<t:{ns}:R>'

def build():
    d = get(FEED); now = d.get('now') or int(time.time()); kills = d.get('kills', {})
    def key(b):
        k = kills.get(b[0]) or {}
        return -1 if k.get('st') == 'up' else int(k.get('ns') or 10**12)
    text = lambda c: {'type': 10, 'content': c}
    sep = {'type': 14, 'divider': True, 'spacing': 1}
    field = '\n'.join(boss_line(n, kills.get(b), now) for b, n in sorted(BOSSES, key=key))
    abyss = '\n'.join(boss_line(n, kills.get(b), now) for b, n in ABYSS)
    comps = [text('## ⏰ ボス時間\n-# ミスランテイダ天族'), sep,
             text(field), sep,
             text('-# アビス\n' + abyss), sep,
             text(f'-# 🕒 最終更新 <t:{now}:t>（<t:{now}:R>）\n-# 討伐報告からの推定。ゲーム内のマップ→探検でも確認できます')]
    return {'flags': 1 << 15, 'components': [{'type': 17, 'accent_color': 0xE67E22, 'components': comps}],
            'allowed_mentions': {'parse': []}}

def send(method, url, body):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json', 'User-Agent': 'aion2-bossboard'})
    x = urllib.request.urlopen(r, timeout=30).read()
    return json.loads(x) if x else None

if __name__ == '__main__':
    hook, mid = os.environ['BOARD_WEBHOOK_URL'], os.environ.get('BOARD_MESSAGE_ID', '')
    body = build()
    if mid:
        send('PATCH', f'{hook}/messages/{mid}?with_components=true', {'components': body['components']})
        print('updated')
    else:
        m = send('POST', hook + '?wait=true&with_components=true', dict(body, flags=body['flags'] | 4096))   # 初回だけ。サイレント
        print('posted', m['id'])
