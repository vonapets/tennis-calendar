#!/usr/bin/env python3
"""Join data/schedule.json + data/context.json into a single self-contained calendar.html."""
import json, datetime, pathlib, sys
ROOT = pathlib.Path(__file__).parent

def main():
    weeks  = json.loads((ROOT/'data'/'schedule.json').read_text())
    ctx    = json.loads((ROOT/'data'/'context.json').read_text())
    events = json.loads((ROOT/'data'/'events.json').read_text())
    chpath = ROOT/'data'/'changes.json'
    changes = json.loads(chpath.read_text()) if chpath.exists() else None
    tpl    = (ROOT/'template.html').read_text()

    # tag the events that the launch plan picks, so both views agree
    picks = set()
    for w in weeks:
        for slot in ('slot1', 'slot2'):
            t = w.get(slot)
            if t and t.get('verdict') in ('launch', 'running'):
                picks.add((t['tour'], t['name']))       # tour+name: dates come from the sync
    for e in events:
        e['pick'] = (e['tour'], e['name']) in picks
    missed = picks - {(e['tour'], e['name']) for e in events if e['pick']}
    if missed:
        print("WARNING: launch picks with no dated event row:",
              ', '.join(f"{t} {n}" for t, n in sorted(missed)))

    # the plan is hand-maintained, the calendar syncs: catch them drifting apart
    # key on tour+name: "China Open" is both the ATP 500 and the WTA 1000 in
    # Beijing, and Cali, Ningbo and Lisboa Belem each name two different events
    dated = {(e['tour'], e['name']): e for e in events}
    drift = []
    for w in weeks:
        for t in [w.get('slot1'), w.get('slot2')] + (w.get('also_on') or []):
            if not t:
                continue
            e = dated.get((t['tour'], t['name']))
            if not e:
                continue
            slack = 1 if e.get('precision') == 'week' else 0   # wiki gives Monday, not the real start
            gap = max(abs((datetime.date.fromisoformat(t[k]) - datetime.date.fromisoformat(e[k])).days)
                      for k in ('start', 'end'))
            if gap > slack:
                drift.append(f"{t['tour']} {t['name']}: plan {t['start']}..{t['end']} "
                             f"vs synced {e['start']}..{e['end']}")
    if drift:
        print("PLAN HAS DRIFTED FROM THE SYNCED CALENDAR - update data/schedule.json:")
        for d in sorted(set(drift)):
            print("   ", d)

    payload = {
        'built':   datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%MZ'),
        'today':   datetime.date.today().isoformat(),
        'weeks':   weeks,
        'events':  events,
        'changes': changes,
        'context': ctx,
    }
    blob = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    if '</script' in blob:                      # cannot break out of the payload tag
        blob = blob.replace('</script', '<\\/script')
    out = tpl.replace('__DATA__', blob)
    (ROOT/'calendar.html').write_text(out)
    (ROOT/'index.html').write_text(out)      # GitHub Pages serves index.html at the root

    # the page is one big inline script: a syntax error renders a blank page
    import shutil, subprocess, tempfile, re as _re2
    if shutil.which('node'):
        body = _re2.findall(r'<script>(.*?)</script>', out, _re2.S)[-1]
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f:
            f.write(body); tmp = f.name
        chk = subprocess.run(['node', '--check', tmp], capture_output=True, text=True)
        if chk.returncode:
            print("PAGE SCRIPT WILL NOT PARSE — calendar.html would render blank:")
            print(chk.stderr.strip()[:600])
            return 1
        print("  page script parses (node --check)")

    bad = []
    for w in weeks:
        for t in [w.get('slot1'), w.get('slot2')] + (w.get('also_on') or []):
            if not t:
                continue
            for k in ('start', 'end'):
                try:
                    datetime.date.fromisoformat(t[k])
                except Exception:
                    bad.append(f"{t['name']}: {k}={t.get(k)!r}")
    if bad:
        print("UNPARSEABLE DATES — fix data/schedule.json:", *bad, sep="\n  ")
        return 1

    # a duplicated top-level class selector silently overrides the earlier rule
    import re as _re, collections as _c
    css = tpl[tpl.find('<style>'):tpl.find('</style>')]
    dupes = {k: v for k, v in _c.Counter(_re.findall(r'^\.([A-Za-z][\w-]*)\s*\{', css, _re.M)).items() if v > 1}
    if dupes:
        print("DUPLICATE CSS CLASS RULES — the later one wins and will break layout:", dupes)
        return 1

    n_t = sum(1 + (1 if w.get('slot2') else 0) + len(w.get('also_on') or []) for w in weeks)
    launches = [w['slot1']['name'] for w in weeks if w.get('slot1')]
    print(f"calendar.html + index.html  {len(out):,} bytes")
    print(f"  {len(weeks)} weeks, {n_t} plan rows, {len(launches)} slot-1 launches")
    print(f"  {len(events)} dated events, {sum(1 for e in events if e['pick'])} tagged as picks")
    print(f"  {weeks[0]['week_start']} -> {weeks[-1]['week_end']}")

if __name__ == '__main__':
    sys.exit(main())
