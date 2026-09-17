#!/usr/bin/env python3
"""Join data/schedule.json + data/context.json into a single self-contained calendar.html."""
import json, datetime, pathlib, sys
ROOT = pathlib.Path(__file__).parent

def main():
    weeks  = json.loads((ROOT/'data'/'schedule.json').read_text())
    ctx    = json.loads((ROOT/'data'/'context.json').read_text())
    events = json.loads((ROOT/'data'/'events.json').read_text())
    tpl    = (ROOT/'template.html').read_text()

    # tag the events that the launch plan picks, so both views agree
    picks = set()
    for w in weeks:
        for slot in ('slot1', 'slot2'):
            t = w.get(slot)
            if t and t.get('verdict') in ('launch', 'running'):
                picks.add((t['name'], t['start']))
    for e in events:
        e['pick'] = (e['name'], e['start']) in picks
    missed = {n for n, _ in picks} - {e['name'] for e in events if e['pick']}
    if missed:
        print("WARNING: launch picks with no dated event row:", ', '.join(sorted(missed)))

    payload = {
        'built':   datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%MZ'),
        'today':   datetime.date.today().isoformat(),
        'weeks':   weeks,
        'events':  events,
        'context': ctx,
    }
    blob = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    if '</script' in blob:                      # cannot break out of the payload tag
        blob = blob.replace('</script', '<\\/script')
    out = tpl.replace('__DATA__', blob)
    (ROOT/'calendar.html').write_text(out)

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
    print(f"calendar.html  {len(out):,} bytes")
    print(f"  {len(weeks)} weeks, {n_t} plan rows, {len(launches)} slot-1 launches")
    print(f"  {len(events)} dated events, {sum(1 for e in events if e['pick'])} tagged as picks")
    print(f"  {weeks[0]['week_start']} -> {weeks[-1]['week_end']}")

if __name__ == '__main__':
    sys.exit(main())
