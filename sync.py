#!/usr/bin/env python3
"""Pull the tennis calendar from its upstream sources and diff against yesterday.

Three independent sources, each of which can fail without taking the page down:

  WTA        api.wtatennis.com          official, exact dates, tour level + WTA 125
  ATP        MediaWiki 2026 ATP Tour    week starts; cites the official ATP PDF
  Challenger MediaWiki 2026 ATP Challenger Tour

atptour.com itself is Cloudflare-blocked to scripted requests (403), including
its own calendar PDF, and protennislive needs a key (401) — the MediaWiki route
is the only automatable ATP source. It is community-maintained, so it lags a
same-day change and is the reason every ATP row carries its source.

Writes data/events.json, data/changes.json. Refuses to publish a gutted pull.

  python3 sync.py            # all sources
  python3 sync.py --dry-run  # parse and diff, write nothing
"""
import json, re, sys, time, datetime, pathlib, urllib.request, urllib.parse, urllib.error

ROOT   = pathlib.Path(__file__).parent
DATA   = ROOT / 'data'
UA     = {'User-Agent': 'tennis-calendar/2.0 (+github.com/vonapets/tennis-calendar)'}
WINDOW = ('2026-09-17', '2026-12-31')
MIN_KEEP_RATIO = 0.60            # a pull under this much of the last one is a gutted fetch

MONTHS = {m: i for i, m in enumerate(
    ['January','February','March','April','May','June','July','August',
     'September','October','November','December'], 1)}
ABBR = {m[:3]: i for m, i in MONTHS.items()}


def get(url, tries=4, as_json=True):
    for a in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45)
            raw = r.read()
            return json.loads(raw) if as_json else raw.decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            time.sleep(.8 * (a + 1))
        except Exception:
            time.sleep(.8 * (a + 1))
    return None


def wikitext(page):
    q = urllib.parse.urlencode({'action': 'parse', 'page': page, 'prop': 'wikitext',
                                'format': 'json', 'formatversion': '2'})
    d = get(f"https://en.wikipedia.org/w/api.php?{q}")
    return (d or {}).get('parse', {}).get('wikitext')


# ---------------------------------------------------------------- WTA
def pull_wta():
    """Official API. Authoritative: exact start and end dates, real tier labels."""
    out, page = [], 0
    LV = {'Grand Slam': 'SLAM', 'Finals': 'Finals', 'WTA 1000': 'WTA 1000',
          'WTA 500': 'WTA 500', 'WTA 250': 'WTA 250', 'WTA 125': 'WTA 125'}
    while page < 12:
        q = urllib.parse.urlencode({'page': page, 'pageSize': 100,
                                    'from': WINDOW[0], 'to': WINDOW[1]})
        d = get(f"https://api.wtatennis.com/tennis/tournaments/?{q}")
        rows = (d or {}).get('content') or (d if isinstance(d, list) else None)
        if not rows:
            break
        for x in rows:
            g = x.get('tournamentGroup') or {}
            if g.get('level') not in LV:
                continue
            sd, ed = x.get('startDate'), x.get('endDate')
            if not sd or not (WINDOW[0] <= sd <= WINDOW[1]):
                continue
            tier = LV[g['level']]
            city = (g.get('name') or '').title().replace(' 125', '')
            out.append(dict(
                name=re.sub(r'\s*-\s*[A-Z]{3}$', '', (x.get('title') or '').split(' - ')[0]).strip() or city,
                city=city, country=x.get('country'),
                tour='WTA-125' if tier == 'WTA 125' else 'WTA', tier=tier,
                surface=x.get('surface') or '', draw=x.get('singlesDrawSize'),
                start=sd, end=ed, precision='exact', src='api.wtatennis.com'))
        page += 1
        if len(rows) < 100:
            break
    return out


# ---------------------------------------------------------------- ATP tour
def pull_atp():
    """MediaWiki. The week cell opens a rowspan block ('|rowspan=4|28 Sep||') and
    the other tournaments in that week carry no date of their own, so slice by
    week marker and take every tournament inside. '5 Oct<br />12 Oct' is a
    two-week event. Separators vary ('|| ' vs ' | '), and the tier line is
    absent on the team events, so pull name/city/country structurally and read
    tier, surface and draw out of whatever the rest of the cell holds."""
    w = wikitext('2026 ATP Tour')
    if not w:
        return None
    month, marks = None, []
    for m in re.finditer(r"===\s*([A-Z][a-z]+)\s*===|"
                         r"\|\s*(?:rowspan=\d+\s*\|)?\s*(\d{1,2})\s+([A-Z][a-z]{2})\s*"
                         r"(?:<br\s*/?>\s*(\d{1,2})\s+([A-Z][a-z]{2})\s*)?\|", w):
        if m.group(1):
            month = MONTHS.get(m.group(1), month)
            continue
        d1, mo1, d2, mo2 = m.group(2), m.group(3), m.group(4), m.group(5)
        try:
            start = datetime.date(2026, ABBR.get(mo1, month or 1), int(d1))
            last = datetime.date(2026, ABBR.get(mo2, ABBR.get(mo1, month or 1)), int(d2)) if d2 else start
        except Exception:
            continue
        marks.append((m.start(), start, last))

    HEAD = re.compile(r"\[\[([^\]\|]+?)(?:\|([^\]]*?))?\]\]\s*<br\s*/?>\s*"
                      r"\[\[([^\]\|]+?)(?:\|[^\]]*?)?\]\]\s*,?\s*([^<|]*)", re.S)
    TIER = re.compile(r"(Grand Slam|Next Gen ATP Finals|ATP Finals|ATP \d+|United Cup|Davis Cup)")
    out, seen = [], set()
    for i, (pos, start, last) in enumerate(marks):
        if not (WINDOW[0] <= start.isoformat() <= WINDOW[1]):
            continue
        blob = w[pos:(marks[i + 1][0] if i + 1 < len(marks) else len(w))]
        end = last + datetime.timedelta(days=6)
        for m in HEAD.finditer(blob):
            name = re.sub(r'^2026\s+', '', (m.group(2) or m.group(1) or '').strip())
            if not name or name.lower().startswith(('flagicon', 'file:')) or (name, start) in seen:
                continue
            rest = blob[m.end():m.end() + 260]
            if '<br' not in blob[m.start():m.end() + 40] or 'vs' == name:
                continue
            tier_m, sf = TIER.search(rest), re.search(r'(Hard|Clay|Grass|Carpet)(\s*\(i\))?', rest)
            if not tier_m and not sf:
                continue                      # not a tournament cell
            seen.add((name, start))
            dr = re.search(r'(\d+)S\b', rest)
            tier = tier_m.group(1) if tier_m else 'Team'
            out.append(dict(name=name, city=(m.group(3) or '').split(',')[0].strip(),
                            country=(m.group(4) or '').strip().strip(',').strip(),
                            tour='ATP',
                            tier=('Finals' if 'Finals' in tier and 'Next Gen' not in tier
                                  else 'Next Gen' if 'Next Gen' in tier
                                  else 'Team' if 'Davis' in tier or tier == 'Team' else tier),
                            surface=(sf.group(1) + (' (i)' if sf.group(2) else '')) if sf else '',
                            draw=int(dr.group(1)) if dr else None,
                            start=start.isoformat(), end=end.isoformat(), precision='week',
                            src='wikipedia:2026 ATP Tour'))
    return out


# ---------------------------------------------------------------- Challenger
def pull_challenger():
    """MediaWiki. Week column is a full '|September 14||' label; weeks run Mon-Sun."""
    w = wikitext('2026 ATP Challenger Tour')
    if not w:
        return None
    out = []
    marks = [(m.start(), m.group(1)) for m in re.finditer(
        r"\|((?:" + "|".join(MONTHS) + r")\s+\d{1,2})\|\|", w)]
    seen_week = set()
    for i, (pos, lab) in enumerate(marks):
        mo, dy = lab.split()
        if lab in seen_week:
            continue
        seen_week.add(lab)
        try:
            d0 = datetime.date(2026, MONTHS[mo], int(dy))
        except Exception:
            continue
        if not (WINDOW[0] <= d0.isoformat() <= WINDOW[1]):
            continue
        blob = w[pos:(marks[i + 1][0] if i + 1 < len(marks) else len(w))]
        seen = set()
        for m in re.finditer(
                r"\[\[([^\]\|]+?)(?:\|([^\]]*?))?\]\](.{0,240}?)(Challenger \d+)\s*[–—-]\s*(\d+)S",
                blob, re.S):
            nm = re.sub(r'^2026\s+', '', (m.group(2) or m.group(1)).strip())
            if nm in seen:
                continue
            seen.add(nm)
            mid = m.group(3)
            loc = re.findall(r"\[\[([^\]\|]+?)(?:\|[^\]]*?)?\]\]", mid)
            ct = re.findall(r",\s*([A-Za-z ]{3,24})", mid)
            sf = re.search(r'(Hard|Clay|Grass|Carpet)(\s*\(i\))?', mid)
            out.append(dict(name=nm, city=(loc[0].split(',')[0] if loc else ''),
                            country=(ct[0].strip() if ct else ''),
                            tour='ATP-CH', tier=m.group(4),
                            surface=(sf.group(1) + (' (i)' if sf.group(2) else '')) if sf else '',
                            draw=int(m.group(5)), start=d0.isoformat(),
                            end=(d0 + datetime.timedelta(days=6)).isoformat(),
                            precision='week', src='wikipedia:2026 ATP Challenger Tour'))
    return out


# ---------------------------------------------------------------- diff
def key(e):
    return (e['tour'], e['name'])


def diff(old, new):
    o = {key(e): e for e in old}
    n = {key(e): e for e in new}
    ch = {'moved': [], 'added': [], 'removed': []}
    for k in n.keys() & o.keys():
        a, b = o[k], n[k]
        if (a['start'], a['end']) != (b['start'], b['end']):
            ch['moved'].append({'name': b['name'], 'tour': b['tour'], 'tier': b['tier'],
                                'was': f"{a['start']}..{a['end']}",
                                'now': f"{b['start']}..{b['end']}"})
    for k in n.keys() - o.keys():
        ch['added'].append({'name': n[k]['name'], 'tour': n[k]['tour'], 'tier': n[k]['tier'],
                            'now': f"{n[k]['start']}..{n[k]['end']}"})
    for k in o.keys() - n.keys():
        ch['removed'].append({'name': o[k]['name'], 'tour': o[k]['tour'], 'tier': o[k]['tier'],
                              'was': f"{o[k]['start']}..{o[k]['end']}"})
    return ch


def main():
    dry = '--dry-run' in sys.argv
    prev = json.loads((DATA / 'events.json').read_text()) if (DATA / 'events.json').exists() else []
    prev_by_src = {}
    for e in prev:
        prev_by_src.setdefault(e.get('tour'), []).append(e)

    status, events = {}, []
    for label, fn, tours in [('wta', pull_wta, ('WTA', 'WTA-125')),
                             ('atp', pull_atp, ('ATP',)),
                             ('challenger', pull_challenger, ('ATP-CH',))]:
        got = fn()
        kept = [e for t in tours for e in prev_by_src.get(t, [])]
        if not got:
            status[label] = f"FAILED - kept {len(kept)} rows from the previous snapshot"
            events += kept
            continue
        if kept and len(got) < MIN_KEEP_RATIO * len(kept):
            status[label] = (f"REFUSED - pulled {len(got)} against {len(kept)} last time "
                             f"(under {MIN_KEEP_RATIO:.0%}); kept the previous snapshot")
            events += kept
            continue
        status[label] = f"ok - {len(got)} tournaments"
        events += got

    events.sort(key=lambda e: (e['start'], e['tour'], e['name']))
    ch = diff(prev, events)

    for k, v in status.items():
        print(f"  {k:<11} {v}")
    n_ch = sum(len(v) for v in ch.values())
    print(f"  {'diff':<11} {len(ch['moved'])} moved, {len(ch['added'])} added, {len(ch['removed'])} removed")
    for m in ch['moved'][:12]:
        print(f"      MOVED  {m['name']}  {m['was']} -> {m['now']}")

    if dry:
        print("\n--dry-run: nothing written")
        return 0
    (DATA / 'events.json').write_text(json.dumps(events, indent=1))
    (DATA / 'changes.json').write_text(json.dumps(
        {'checked': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%MZ'),
         'sources': status, 'changes': ch}, indent=1))
    print(f"\nwrote data/events.json ({len(events)}) and data/changes.json ({n_ch} changes)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
