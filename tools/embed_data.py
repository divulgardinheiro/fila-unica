#!/usr/bin/env python3
"""Embute data.json no FALLBACK do index.html (entre /*__DATA__*/ e /*__END__*/).

Rodar apos qualquer edicao de data.json:  python3 tools/embed_data.py
"""
import json
import pathlib
import re

root = pathlib.Path(__file__).resolve().parent.parent
data = json.loads((root / "data.json").read_text(encoding="utf-8"))
html = (root / "index.html").read_text(encoding="utf-8")

payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
payload = payload.replace("</", "<\\/")  # nao fechar a tag <script>

novo, n = re.subn(
    r"/\*__DATA__\*/.*?/\*__END__\*/",
    lambda _: f"/*__DATA__*/{payload}/*__END__*/",
    html,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit("marcadores __DATA__/__END__ nao encontrados no index.html")

(root / "index.html").write_text(novo, encoding="utf-8")
print(f"FALLBACK atualizado ({len(payload)} bytes de data.json)")
