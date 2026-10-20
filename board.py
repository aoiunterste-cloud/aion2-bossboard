# ミスランテイダ天族のボス時間を Discord の 1 つのメッセージに書き換え続ける（GitHub Actions から 5 分おき）
# データ: フィールドボスは Aion2 Timers の討伐報告（推定）、アグロは決まった時刻
import json, os, time, urllib.request, datetime as dt

FEED = 'https://www.aion2timers.com/api/fieldboss.php?action=feed&server=jp-meslamtaeda'
BOSSES = [('elyos22', 'カシャパ'), ('elyos21', 'タルタン'), ('elyos24', 'ガルトゥア'), ('elyos23', 'ラグタ')]
WINDOW = 10 * 60                      # 予定時刻から湧くまでの幅（Aion2 Timers の値）
JST = dt.timezone(dt.timedelta(hours=9))
ARGO_DAYS, ARGO_HM = (0, 3, 5), (21, 30)  # 月・木・土 21:30（公式ガイドは水・土 22:30 で割れ）

def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'aion2-bossboard'}), timeout=30))

def next_argo(now):
    t = dt.datetime.fromtimestamp(now, JST)
    for d in range(8):
        c = (t + dt.timedelta(days=d)).replace(hour=ARGO_HM[0], minute=ARGO_HM[1], second=0, microsecond=0)
        if c.weekday() in ARGO_DAYS and c.timestamp() > now - 30 * 60:
            return int(c.timestamp())

def boss_block(name, k, now):
    """1 体ぶん: 大きい見出し（名前と時刻）＋小さい字（あと何分）"""
    if not k:
        return f'### {name}\n-# 情報なし'
    if k.get('st') == 'up':
        hp = f"・HP {k['hp'][0]}%" if k.get('hp') else ''
        return f'### 🔴 {name}　出現中\n-# 湧いています{hp}'
    ns = int(k.get('ns') or 0)
    if not ns:
        return f'### {name}\n-# 情報なし'
    if ns <= now:
        return f'### 🟡 {name}　まもなく\n-# 湧き待ち・<t:{ns + WINDOW}:t> ごろまで'
    mark = '🟠 ' if ns - now <= 3600 else ''
    return f'### {mark}{name}　<t:{ns}:t>\n-# <t:{ns}:R>'

WEEK = '月火水木金土日'

def build():
    d = get(FEED); now = d.get('now') or int(time.time()); kills = d.get('kills', {})
    def key(b):
        k = kills.get(b[0]) or {}
        return -1 if k.get('st') == 'up' else int(k.get('ns') or 10**12)
    blocks = [boss_block(name, kills.get(bid), now) for bid, name in sorted(BOSSES, key=key)]
    a = next_argo(now); ad = dt.datetime.fromtimestamp(a, JST)
    argo = (f'### 🔴 アグロ　出現中\n-# <t:{a}:t> から' if a <= now
            else f'### アグロ　{WEEK[ad.weekday()]}曜 {ad:%H:%M}\n-# <t:{a}:R>')
    text = lambda c: {'type': 10, 'content': c}
    sep = {'type': 14, 'divider': True, 'spacing': 1}
    comps = [text('## ⏰ ボス時間\n-# ミスランテイダ天族'), sep]
    for b in blocks: comps.append(text(b))
    comps += [sep, text('-# アビス'), text(argo), sep,
              text(f'-# 🕒 最終更新 <t:{now}:t>（<t:{now}:R>）\n-# 討伐報告からの推定。アグロは月木土 21:30（資料で割れ）。ゲーム内のマップ→探検でも確認できます')]
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
