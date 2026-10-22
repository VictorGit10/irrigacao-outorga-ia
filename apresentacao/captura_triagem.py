"""
Tira a imagem da tela de triagem usada no slide "triagem" e na página inicial.

Abre docs/triagem/index.html num navegador sem janela (Playwright + Chromium),
vai para o caso C-02 e recorta a área principal da tela.

Uso:  pip install playwright && playwright install chromium
      python captura_triagem.py   -> docs/apresentacao/img/7_triagem.png
"""
import os
from playwright.sync_api import sync_playwright

AQUI = os.path.dirname(os.path.abspath(__file__))
PAGINA = os.path.abspath(os.path.join(AQUI, "..", "docs", "triagem", "index.html"))
SAIDA = os.path.join(AQUI, "..", "docs", "apresentacao", "img", "7_triagem.png")

with sync_playwright() as p:
    nav = p.chromium.launch()
    pg = nav.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=1.5)
    pg.goto("file:///" + PAGINA.replace("\\", "/"))
    pg.evaluate("localStorage.clear()")
    pg.reload()
    pg.click("#avisoTopo button")          # fecha o aviso do topo
    pg.click(".pill[data-id='C-02']")
    pg.wait_for_timeout(500)
    pg.locator(".grade").screenshot(path=SAIDA)
    nav.close()
print("ok:", os.path.normpath(SAIDA))
