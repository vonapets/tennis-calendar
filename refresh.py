#!/usr/bin/env python3
"""Re-pull traded volume from the two reference venues, Kalshi and Polymarket.

Updates data/context.json in place. It does NOT touch data/schedule.json — nothing
publishes Challenger or ITF draws in a machine feed, so the calendar itself is
hand-maintained. See README.

  python3 refresh.py             # both venues
  python3 refresh.py polymarket  # just one
"""
import json, pathlib, sys, time, urllib.request, urllib.parse, urllib.error, collections, re, statistics

ROOT = pathlib.Path(__file__).parent
UA   = {'User-Agent': 'tennis-calendar/1.0', 'Accept': 'application/json'}

def get(url, tries=4):
    for a in range(tries):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45))
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 422):
                return None
            time.sleep(.7 * (a + 1))
        except Exception:
            time.sleep(.7 * (a + 1))
    return None

# ---------------------------------------------------------------- Kalshi
KSER = {
    'tour_level':     ['KXATPMATCH', 'KXWTAMATCH'],
    'atp_challenger': ['KXATPCHALLENGERMATCH'],
    'wta_125':        ['KXWTACHALLENGERMATCH'],
    'itf':            ['KXITFMATCH', 'KXITFWMATCH'],
}
_RULE  = re.compile(r'match in the (.+?) after a ball', re.I)
_ROUND = re.compile(r'\s+(Final|Semifinal|Quarterfinal|Round [Oo]f \d+|Round \d+|Qualif\w*.*|R\d+)$', re.I)

def kalshi():
    base = "https://api.elections.kalshi.com/trade-api/v2"
    res = {}
    for tier, series in KSER.items():
        per = collections.defaultdict(float)
        for s in series:
            cur = None
            while True:
                q = {'series_ticker': s, 'limit': 1000}
                if cur:
                    q['cursor'] = cur
                d = get(f"{base}/markets?{urllib.parse.urlencode(q)}")
                if not d or not d.get('markets'):
                    break
                for m in d['markets']:
                    r = _RULE.search(m.get('rules_primary') or '')
                    if not r:
                        continue
                    name = r.group(1).strip()
                    for _ in range(3):
                        name = _ROUND.sub('', name).strip()
                    per[re.sub(r'^20\d\d\s+', '', name)] += float(m.get('volume_fp') or 0)
                cur = d.get('cursor')
                if not cur:
                    break
        vals = [v for v in per.values() if v > 0]
        res[tier] = {'total': round(sum(vals)), 'tournaments': len(vals),
                     'median': round(statistics.median(vals)) if vals else 0}
        print(f"  kalshi {tier:<16} ${res[tier]['total']:>16,}  n={res[tier]['tournaments']}")
    return res

# ---------------------------------------------------------------- Polymarket
def polymarket():
    """Open tennis events, moneyline market only."""
    PROP = re.compile(r'set\b|games|tiebreak|handicap|spread|total|o/u|over/under|completed match', re.I)
    evs = {}
    for tag in ('tennis', 'atp', 'wta'):
        off = 0
        while off <= 2000:
            q = urllib.parse.urlencode({'tag_slug': tag, 'limit': 100, 'offset': off, 'closed': 'false'})
            d = get(f"https://gamma-api.polymarket.com/events?{q}")
            if not isinstance(d, list) or not d:
                break
            for e in d:
                evs[e.get('id')] = e
            if len(d) < 100:
                break
            off += 100
    def ml(e):
        mk = e.get('markets') or []
        if not mk:
            return 0.0
        v = lambda m: float(m.get('volume') or 0)
        if len(mk) == 1:
            return v(mk[0])
        title = (e.get('title') or '').strip()
        c = [m for m in mk if not (m.get('groupItemTitle') or '').strip()
             or (m.get('question') or '').strip() == title]
        c = [m for m in c if not PROP.search(m.get('question') or '')] or mk
        return max(map(v, c))
    return {'open_events': len(evs),
            'open_moneyline_volume': round(sum(ml(e) for e in evs.values())),
            'pulled': time.strftime('%Y-%m-%d')}

def main():
    which = sys.argv[1:] or ['kalshi', 'polymarket']
    path = ROOT / 'data' / 'context.json'
    ctx = json.loads(path.read_text())
    if 'kalshi' in which:
        print("kalshi…");     k = kalshi()
        ctx['kalshi_medians'] = {**ctx.get('kalshi_medians', {}),
                                 **{t: v['median'] for t, v in k.items()}}
        ctx['kalshi_detail'] = k
    if 'polymarket' in which:
        print("polymarket…"); ctx['polymarket_live'] = polymarket()
        print("  ", ctx['polymarket_live'])
    path.write_text(json.dumps(ctx, indent=2))
    print(f"\nwrote {path}. Run ./build.py to regenerate calendar.html")

if __name__ == '__main__':
    sys.exit(main())
