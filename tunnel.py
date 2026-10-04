import os
import re
import sys
import time
import subprocess
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")

_public_url = None
_tunnel_process = None
_lock = threading.Lock()

def get_public_url():
    global _public_url
    return _public_url

def save_url_files(url):
    try:
        txt_path = os.path.join(BASE_DIR, "link_celular_4g_5g.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  LINK DE ACESSO PARA CELULAR (4G / 5G / QUALQUER LUGAR)\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Acesse no celular: {url}\n\n")
            f.write("(Funciona em qualquer lugar do mundo, sem precisar de Wi-Fi!)\n")
            f.write(f"Atualizado em: {time.strftime('%d/%m/%Y %H:%M:%S')}\n")

        html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Shopee Downloader - Acesso Celular</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
</head>
<body class="bg-slate-950 text-white min-h-screen flex items-center justify-center p-4 font-sans">
    <div class="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full text-center shadow-2xl">
        <h2 class="text-xl font-bold text-orange-500 mb-2">Shopee Downloader PRO</h2>
        <p class="text-xs text-slate-400 mb-4">Aponte a câmera do seu celular (4G / 5G / Wi-Fi):</p>
        <div id="qrcode" class="bg-white p-3 rounded-2xl inline-block shadow-lg mx-auto mb-4"></div>
        <a href="{url}" target="_blank" class="block w-full py-2.5 bg-orange-500 hover:bg-orange-600 text-white font-semibold rounded-xl text-sm transition-colors mb-2">
            Abrir Link no Navegador
        </a>
        <p class="text-[11px] text-slate-500 font-mono break-all">{url}</p>
    </div>
    <script>
        new QRCode(document.getElementById("qrcode"), {{
            text: "{url}",
            width: 180,
            height: 180,
            colorDark: "#0F172A",
            colorLight: "#FFFFFF",
            correctLevel: QRCode.CorrectLevel.M
        }});
    </script>
</body>
</html>"""
        html_path = os.path.join(BASE_DIR, "Acessar_no_Celular_4G_5G.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    except Exception as e:
        print(f"[Tunnel] Erro ao salvar arquivo txt/html: {e}")

def _run_tunnel_loop():
    global _public_url, _tunnel_process
    if not os.path.exists(CLOUDFLARED_EXE):
        print(f"[Tunnel] cloudflared.exe não encontrado em {CLOUDFLARED_EXE}")
        return

    startupinfo = None
    creationflags = 0
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        creationflags = subprocess.CREATE_NO_WINDOW

    while True:
        try:
            cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:8000"]
            print("[Tunnel] Iniciando túnel Cloudflare seguro para acesso 4G/5G...")
            
            _tunnel_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                startupinfo=startupinfo,
                creationflags=creationflags
            )

            # Lê logs para encontrar a URL pública e continua drenando o stderr
            while _tunnel_process.poll() is None:
                line = _tunnel_process.stderr.readline()
                if not line:
                    time.sleep(0.1)
                    continue
                match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
                if match:
                    found_url = match.group(0)
                    with _lock:
                        if _public_url != found_url:
                            _public_url = found_url
                            print("=" * 65)
                            print(f">> [TÚNEL ONLINE 4G/5G] Link Público: {found_url}")
                            print("=" * 65)
                            save_url_files(found_url)

            # Mantém processo rodando e monitorando
            _tunnel_process.wait()
            print("[Tunnel] Processo do túnel encerrou, reiniciando em 5 segundos...")
        except Exception as err:
            print(f"[Tunnel] Erro no túnel: {err}")
        
        time.sleep(5)

def start_tunnel():
    t = threading.Thread(target=_run_tunnel_loop, daemon=True)
    t.start()
    return t
