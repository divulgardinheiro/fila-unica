#!/usr/bin/env python3
"""Separa data.source.json (sensivel, fora do git) em:
  - data.public.json  : subconjunto SEM PII (contagens, categorias, graficos)  -> commit
  - work.enc.json     : detalhe de trabalho (nomes, processos, minutas) CIFRADO -> commit
  - privado.enc.json  : fila pessoal, ja cifrada com a senha pessoal            -> commit
E embute data.public.json no FALLBACK do index.html.

Senhas ficam em .secrets/ (fora do git). Rodar apos editar data.source.json:
    python3 tools/build.py
"""
import base64
import json
import os
import pathlib
import re

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ROOT = pathlib.Path(__file__).resolve().parent.parent


def cifrar(obj, senha):
    plain = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(16)
    iv = os.urandom(12)
    iters = 200000
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iters).derive(senha.encode())
    ct = AESGCM(key).encrypt(iv, plain, None)
    return {
        "v": 1, "kdf": "PBKDF2-SHA256", "iter": iters,
        "salt": base64.b64encode(salt).decode(),
        "iv": base64.b64encode(iv).decode(),
        "ct": base64.b64encode(ct).decode(),
    }


def main():
    src = json.loads((ROOT / "data.source.json").read_text(encoding="utf-8"))
    team_pass = (ROOT / ".secrets" / "team.pass").read_text().strip()

    # ---- PUBLICO: sem nomes, sem numeros de processo, sem dado sensivel ----
    publico = {
        "atualizadoEm": src.get("atualizadoEm"),
        "origens": src.get("origens", []),
        "grupos": src.get("grupos", []),
        "categorias": src.get("categorias", []),
        "filaPolitica": src.get("filaPolitica", ""),
        "sei": {"capturadoEm": src.get("sei", {}).get("capturadoEm"),
                "resumo": src.get("sei", {}).get("resumo", {})},
        "pje": src.get("pje", {}),  # so contagens/tipos, sem nomes
        "esiest": {"periodo": src.get("esiest", {}).get("periodo"),
                   "limiarDias": src.get("esiest", {}).get("limiarDias")},
        "temTrabalho": True,  # sinaliza que ha detalhe cifrado a destrancar
    }

    # ---- TRABALHO: tudo que tem nome/processo/minuta (cifrado) ----
    trabalho = {
        "notaOutlook": src.get("nota", ""),
        "tarefas": src.get("tarefas", []),
        "seiNota": src.get("sei", {}).get("nota", ""),
        "seiProcessos": src.get("sei", {}).get("processos", []),
        "esiestNota": src.get("esiest", {}).get("nota", ""),
        "esiestProcessos": src.get("esiest", {}).get("processos", []),
        "radar": src.get("radar", {}),
        "solicitacoes": src.get("solicitacoes", {}),
        "lembretes": src.get("lembretes", []),
        "pessoal": src.get("pessoal", {}),
    }

    (ROOT / "data.public.json").write_text(json.dumps(publico, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "work.enc.json").write_text(json.dumps(cifrar(trabalho, team_pass)), encoding="utf-8")

    # ---- embutir SO o publico no FALLBACK ----
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    payload = json.dumps(publico, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    novo, n = re.subn(r"/\*__DATA__\*/.*?/\*__END__\*/",
                      lambda _: f"/*__DATA__*/{payload}/*__END__*/", html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("marcadores __DATA__ nao encontrados")
    (ROOT / "index.html").write_text(novo, encoding="utf-8")

    print("data.public.json:", (ROOT / "data.public.json").stat().st_size, "bytes")
    print("work.enc.json:", (ROOT / "work.enc.json").stat().st_size, "bytes (cifrado)")
    print("FALLBACK publico embutido")


if __name__ == "__main__":
    main()
