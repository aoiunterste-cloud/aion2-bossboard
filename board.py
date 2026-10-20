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

def build():
    d = get(FEED); now = d.get('now') or int(time.time()); kills = d.get('kills', {})
    alive, soon, later = [], [], []
    for bid, name in BOSSES:
        k = kills.get(bid)
        if not k:
            later.append((10**12, f'**{name}**　情報なし')); continue
        if k.get('st') == 'up':
            hp = f"・HP {k['hp'][0]}%" if k.get('hp') else ''
            alive.append((0, f'🔴 **{name}**　出現中{hp}'))
        elif k.get('ns'):
            ns = int(k['ns'])
            if ns <= now:
                alive.append((ns, f'🟡 **{name}**　湧き待ち（<t:{ns + WINDOW}:t> ごろまで）'))
            elif ns - now <= 3600:
                soon.append((ns, f'🟠 **{name}**　<t:{ns}:t>（<t:{ns}:R>）'))
            else:
                later.append((ns, f'**{name}**　<t:{ns}:t>（<t:{ns}:R>）'))
    a = next_argo(now)
    argo = f'🔴 **アグロ**　出現中（<t:{a}:t> から）' if a <= now else f'**アグロ**　<t:{a}:f>（<t:{a}:R>）'
    lines = [x[1] for x in sorted(alive)] + [x[1] for x in sorted(soon)] + [x[1] for x in sorted(later)]
    desc = '\n'.join(lines) + '\n\n**アビス**\n' + argo
    return {'embeds': [{
        'title': '⏰ ボス時間（ミスランテイダ天族）',
        'description': desc,
        'color': 0xE67E22,
        'footer': {'text': '討伐報告からの推定・5 分ごとに更新。アグロは月木土 21:30（資料で割れ）。ゲーム内のマップ→探検でも確認できます'},
        'timestamp': dt.datetime.fromtimestamp(now, dt.timezone.utc).isoformat(),
    }], 'allowed_mentions': {'parse': []}}

def send(method, url, body):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode(),
                               headers={'Content-Type': 'application/json', 'User-Agent': 'aion2-bossboard'})
    x = urllib.request.urlopen(r, timeout=30).read()
    return json.loads(x) if x else None

if __name__ == '__main__':
    hook, mid = os.environ['BOARD_WEBHOOK_URL'], os.environ.get('BOARD_MESSAGE_ID', '')
    body = build()
    if mid:
        send('PATCH', f'{hook}/messages/{mid}', body)
        print('updated')
    else:
        m = send('POST', hook + '?wait=true', dict(body, flags=4096))   # 初回だけ。サイレント
        print('posted', m['id'])
