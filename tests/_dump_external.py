import os, re, html, ctypes, xml.etree.ElementTree as ET
from ctypes import wintypes

def read_shared(p):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    h = k.CreateFileW(p, 0x80000000, 0x07, None, 3, 0x80, None)
    sz = k.GetFileSize(h, None)
    buf = ctypes.create_string_buffer(sz)
    rd = wintypes.DWORD(0)
    k.ReadFile(h, buf, sz, ctypes.byref(rd), None)
    k.CloseHandle(h)
    return buf.raw[:rd.value].decode('utf-8', errors='replace')

cfg = os.path.join(os.environ.get('PROGRAMDATA','C:/ProgramData'), 'vMix', 'settingbackups', 'current.config')
content = read_shared(cfg)

for name in ('External', 'External2', 'External3', 'External4',
             'OutputsExternal', 'OutputsExternal2'):
    m = re.search(rf'name="{re.escape(name)}"[^>]*>\s*<value>(.*?)</value>', content, re.DOTALL)
    if not m:
        print(f'\n[{name}] NOT FOUND')
        continue
    decoded = html.unescape(m.group(1).strip())
    print(f'\n=== {name} ===')
    try:
        sub = ET.fromstring(f'<root>{decoded}</root>')
        for child in sub:
            print(f'  {child.tag:<42} {repr(child.text or "")}')
    except Exception as e:
        print('ParseError:', e)
        print(decoded[:1000])
