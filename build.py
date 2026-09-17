#!/usr/bin/env python3
"""Join data/schedule.json + data/context.json into a single self-contained calendar.html."""
import json, datetime, pathlib, sys
ROOT = pathlib.Path(__file__).parent

def main():
    weeks = json.loads((ROOT/'data'/'schedule.json').read_text())
    ctx   = json.loads((ROOT/'data'/'context.json').read_text())
    tpl   = (ROOT/'template.html').read_text()

    payload = {
        'built':   datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y %H:%MZ'),
        'weeks':   weeks,
        'context': ctx,
    }
    blob = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    if '</script' in blob:                      # cannot break out of the payload tag
        blob = blob.replace('</script', '<\\/script')
    out = tpl.replace('__DATA__', blob)
    (ROOT/'calendar.html').write_text(out)

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

    n_t = sum(1 + (1 if w.get('slot2') else 0) + len(w.get('also_on') or []) for w in weeks)
    launches = [w['slot1']['name'] for w in weeks if w.get('slot1')]
    print(f"calendar.html  {len(out):,} bytes")
    print(f"  {len(weeks)} weeks, {n_t} tournament rows, {len(launches)} slot-1 launches")
    print(f"  {weeks[0]['week_start']} -> {weeks[-1]['week_end']}")

if __name__ == '__main__':
    sys.exit(main())
