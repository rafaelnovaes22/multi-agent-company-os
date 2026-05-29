"""Loaders L0 (C5) — carregam o contexto estratégico (DNA, ICP, ofertas) UMA vez
por processo e cacheiam (helper pattern BMAD). Agentes L1/L2 herdam; ninguém
redefine o ICP localmente (C8). Ver 02-ARQUITETURA.md (camada L0) e company/icp.md.
"""
from __future__ import annotations
import os

_COMPANY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "company")
_cache: dict = {}


def _load_doc(name: str, refresh: bool = False) -> dict:
    if not refresh and name in _cache:
        return _cache[name]
    path = os.path.join(_COMPANY_DIR, f"{name}.md")
    if not os.path.exists(path):
        return {"path": path, "text": "", "present": False}
    with open(path, encoding="utf-8") as f:
        text = f.read()
    _cache[name] = {"path": path, "text": text, "present": True}
    return _cache[name]


def load_icp(refresh: bool = False) -> dict:
    """Carrega o ICP (company/icp.md). Cacheado — chamadas seguintes não releem o arquivo."""
    return _load_doc("icp", refresh)


def load_dna(refresh: bool = False) -> dict:
    """Carrega o DNA da empresa (company/dna.md), se existir."""
    return _load_doc("dna", refresh)


def load_offerings(refresh: bool = False) -> dict:
    """Carrega o catálogo de ofertas (company/offerings.md), se existir."""
    return _load_doc("offerings", refresh)
