"""CSV из OCR (data/ocr_raw/*.csv) -> data/dated/*.json"""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'ocr_raw')
OUT = os.path.join(ROOT, 'data', 'dated')
PROGRAM = {
 'sestrinskoe-delo-o-zaochn': ('34.03.01', 'Сестринское дело', 'очно-заочная'),
 'socialnaya-rabota-bakalavriat-zaochn': ('39.03.02', 'Социальная работа (бакалавриат)', 'заочная'),
 'socialnaya-rabota-magistratura-zaochn': ('39.04.02', 'Социальная работа (магистратура)', 'заочная'),
 'obschestvennoe-zdravoobranenie-magistratura-o-zaochn': ('32.04.01', 'Общественное здравоохранение (магистратура)', 'очно-заочная'),
 'obschestvennoe-zdravoohranenie-magistratura-o-zaochn': ('32.04.01', 'Общественное здравоохранение (магистратура)', 'очно-заочная'),
}
TEACH = re.compile(r'[,;]?\s*((?:доц|проф|ст\.?\s?преп|асс|преп)[а-яё.]*\s*[А-ЯЁ][а-яё\-]+(?:\s+[А-ЯЁ]\.\s?[А-ЯЁ]?\.?)?)\s*$')
def main():
    os.makedirs(OUT, exist_ok=True)
    for fn in sorted(os.listdir(RAW)):
        if not fn.endswith('.csv'): continue
        key = fn[:-4]; base = key.split('__')[0]
        code, program, form = PROGRAM.get(base, ('', base, 'заочная'))
        group = ''; course = int(re.sub(r'\D', '', key.split('__')[-1]) or 0)
        rows = []
        for line in open(os.path.join(RAW, fn), encoding='utf-8'):
            line = line.strip()
            if not line: continue
            if line.startswith('##'):
                k, _, v = line[2:].partition('=')
                if k == 'GROUP': group = v.strip()
                continue
            parts = line.split('|')
            if len(parts) < 4: continue
            d, t, s = parts[0].strip(), parts[1].strip(), parts[2].strip()
            p = parts[3].strip() if len(parts) > 3 else ''
            k = parts[4].strip() if len(parts) > 4 else 'Практика'
            m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', d)
            m2 = re.match(r'^(\d{1,2})[:.](\d{2})-(\d{1,2})[:.](\d{2})$', t)
            if not m or not m2 or not s: continue
            tm = TEACH.search(s); teacher = ''
            if tm:
                teacher = tm.group(1).strip(' ,;'); s = s[:tm.start()].strip(' ,;')
            pm = re.match(r'^.*?\((.*)\)\s*$', p)
            if pm and ',' in pm.group(1):
                p = pm.group(1).strip()
            rows.append({'d': f'{m.group(3)}-{m.group(2)}-{m.group(1)}',
                         'ts': f'{int(m2.group(1)):02d}:{m2.group(2)}',
                         'te': f'{int(m2.group(3)):02d}:{m2.group(4)}',
                         'subject': s, 'teacher': teacher, 'place': p,
                         'type': {'лекция':'lecture','практика':'practice','экзамен':'exam'}.get(k.lower(),'practice')})
        # дедупликация
        seen=set(); uniq=[]
        for r in rows:
            sig=json.dumps(r,ensure_ascii=False,sort_keys=True)
            if sig in seen: continue
            seen.add(sig); uniq.append(r)
        dates = sorted({r['d'] for r in uniq})
        payload = {'key': key, 'group': group or key.split('__')[-1], 'code': code, 'program': program,
                   'course': course, 'form': form, 'period': [dates[0], dates[-1]] if dates else [],
                   'lessons': uniq}
        json.dump(payload, open(os.path.join(OUT, key+'.json'),'w',encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"{key}: {payload['group']}, {len(uniq)} занятий, {payload['period']}")
if __name__ == '__main__':
    sys.exit(main())
