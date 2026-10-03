import os
import sys
import io
import zipfile
import re
import urllib.parse
from typing import List, Optional

# Garante diretório de trabalho e sys.path corretos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Garante que stdout e stderr nunca sejam nulos sob pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import httpx
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import tunnel
from scraper import ShopeeScraper, clean_filename

app = FastAPI(title="Shopee Media & Data Downloader Pro", version="1.0.0")

# Habilita CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Inicia o túnel Cloudflare apenas se cloudflared.exe estiver presente (ambiente local Windows)
    if os.path.exists(tunnel.CLOUDFLARED_EXE):
        tunnel.start_tunnel()


scraper = ShopeeScraper()

class ExtractRequest(BaseModel):
    url: str

class DescriptionDownloadRequest(BaseModel):
    title: str
    price: Optional[str] = ""
    original_url: Optional[str] = ""
    description: str
    attributes: Optional[List[dict]] = []

class ImagesZipRequest(BaseModel):
    title: str
    images: List[str]

class BundleZipRequest(BaseModel):
    title: str
    description: str
    price: Optional[str] = ""
    original_url: Optional[str] = ""
    attributes: Optional[List[dict]] = []
    images: List[str]
    video_url: Optional[str] = None

@app.post("/api/extract")
async def extract_product(req: ExtractRequest):
    if not req.url or not req.url.strip():
        raise HTTPException(status_code=400, detail="Por favor, forneça um link válido da Shopee.")
    try:
        data = await scraper.extract_product_info(req.url.strip())
        if not data.get("title") and not data.get("images"):
            raise HTTPException(status_code=404, detail="Não foi possível extrair os dados do produto. Verifique se o link está correto e ativo.")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar o produto: {str(e)}")

@app.get("/api/download/video")
async def download_video(video_url: str = Query(...), title: str = Query("produto-shopee")):
    """Baixa o vídeo diretamente com nome de arquivo amigável e cabeçalhos apropriados."""
    clean_name = clean_filename(title)
    filename = f"{clean_name}-video.mp4"
    
    # Sanitiza a URL do vídeo
    v_url = video_url.strip().replace(r'\/', '/').replace('\\u002F', '/')

    headers_list = [
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": "https://shopee.com.br/",
            "Accept": "*/*",
        },
        {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15",
            "Referer": "https://shopee.com.br/",
        },
        {
            "User-Agent": "okhttp/3.14.9",
        }
    ]

    for headers in headers_list:
        try:
            async with httpx.AsyncClient(timeout=90.0, follow_redirects=True, verify=False) as client:
                resp = await client.get(v_url, headers=headers)
                if resp.status_code in [200, 206] and len(resp.content) > 1000:
                    return StreamingResponse(
                        io.BytesIO(resp.content),
                        media_type="video/mp4",
                        headers={
                            "Content-Disposition": f'attachment; filename="{filename}"',
                            "Content-Length": str(len(resp.content)),
                            "Access-Control-Expose-Headers": "Content-Disposition"
                        }
                    )
        except Exception as err:
            print(f"Tentativa de download de vídeo falhou: {err}")

    # Fallback com urllib
    try:
        import urllib.request
        req = urllib.request.Request(v_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            if len(content) > 1000:
                return StreamingResponse(
                    io.BytesIO(content),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"',
                        "Content-Length": str(len(content)),
                    }
                )
    except Exception as err2:
        print(f"Fallback urllib falhou: {err2}")

    raise HTTPException(status_code=400, detail="Não foi possível obter o fluxo de vídeo da CDN da Shopee.")

@app.post("/api/download/images-zip")
async def download_images_zip(req: ImagesZipRequest):
    """Baixa todas as imagens em alta resolução e gera um arquivo ZIP."""
    if not req.images:
        raise HTTPException(status_code=400, detail="Nenhuma imagem fornecida para download.")

    zip_buffer = io.BytesIO()
    clean_name = clean_filename(req.title)

    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://shopee.com.br/"
        }

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, img_url in enumerate(req.images, start=1):
                try:
                    resp = await client.get(img_url, headers=headers)
                    if resp.status_code == 200:
                        # Determina extensão
                        ext = "jpg"
                        content_type = resp.headers.get("content-type", "")
                        if "png" in content_type:
                            ext = "png"
                        elif "webp" in content_type:
                            ext = "webp"
                        
                        img_filename = f"{clean_name}-imagem-{idx:02d}.{ext}"
                        zf.writestr(img_filename, resp.content)
                except Exception as err:
                    print(f"Erro ao baixar imagem {img_url}: {err}")

    zip_buffer.seek(0)
    zip_filename = f"{clean_name}-imagens.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_filename}"'
        }
    )

@app.post("/api/download/description-txt")
async def download_description_txt(req: DescriptionDownloadRequest):
    """Gera e retorna um arquivo .txt formatado com título, ficha técnica e descrição."""
    clean_name = clean_filename(req.title)
    
    txt_content = []
    txt_content.append("=" * 70)
    txt_content.append(f"PRODUTO: {req.title}")
    if req.price:
        txt_content.append(f"PREÇO: {req.price}")
    if req.original_url:
        txt_content.append(f"LINK DO PRODUTO: {req.original_url}")
    txt_content.append("=" * 70)
    txt_content.append("")

    if req.attributes and len(req.attributes) > 0:
        txt_content.append("--- ESPECIFICAÇÕES / FICHA TÉCNICA ---")
        for attr in req.attributes:
            txt_content.append(f"• {attr.get('name', '')}: {attr.get('value', '')}")
        txt_content.append("")

    txt_content.append("--- DESCRIÇÃO COMPLETA DO PRODUTO ---")
    txt_content.append(req.description or "Sem descrição disponível.")
    txt_content.append("")
    txt_content.append("=" * 70)
    txt_content.append("Extraído via Baixador de Mídias Shopee Pro")
    txt_content.append("=" * 70)

    final_text = "\n".join(txt_content)
    text_bytes = final_text.encode("utf-8")
    filename = f"{clean_name}-descricao.txt"

    return StreamingResponse(
        io.BytesIO(text_bytes),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(text_bytes))
        }
    )

@app.post("/api/download/bundle-zip")
async def download_bundle_zip(req: BundleZipRequest):
    """Gera um pacote completo em ZIP contendo Vídeo + Imagens + Descrição TXT."""
    zip_buffer = io.BytesIO()
    clean_name = clean_filename(req.title)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://shopee.com.br/"
        }

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Arquivo de descrição TXT
            txt_lines = [
                "=" * 70,
                f"PRODUTO: {req.title}",
                f"PREÇO: {req.price or 'N/A'}",
                f"LINK: {req.original_url or 'N/A'}",
                "=" * 70,
                "",
            ]
            if req.attributes:
                txt_lines.append("--- ESPECIFICAÇÕES ---")
                for attr in req.attributes:
                    txt_lines.append(f"• {attr.get('name', '')}: {attr.get('value', '')}")
                txt_lines.append("")
            txt_lines.append("--- DESCRIÇÃO ---")
            txt_lines.append(req.description or "")
            zf.writestr(f"{clean_name}/descricao.txt", "\n".join(txt_lines).encode("utf-8"))

            # 2. Imagens
            for idx, img_url in enumerate(req.images, start=1):
                try:
                    resp = await client.get(img_url, headers=headers)
                    if resp.status_code == 200:
                        ext = "jpg"
                        if "png" in resp.headers.get("content-type", ""):
                            ext = "png"
                        elif "webp" in resp.headers.get("content-type", ""):
                            ext = "webp"
                        zf.writestr(f"{clean_name}/imagens/foto_{idx:02d}.{ext}", resp.content)
                except Exception as err:
                    print(f"Erro ao baixar imagem para bundle: {err}")

            # 3. Vídeo (se houver)
            if req.video_url:
                try:
                    v_resp = await client.get(req.video_url, headers=headers)
                    if v_resp.status_code == 200:
                        zf.writestr(f"{clean_name}/video.mp4", v_resp.content)
                except Exception as err:
                    print(f"Erro ao baixar vídeo para bundle: {err}")

    zip_buffer.seek(0)
    bundle_filename = f"{clean_name}-PACOTE-COMPLETO.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{bundle_filename}"'
        }
    )

@app.get("/api/download/single-image")
async def download_single_image(url: str = Query(...), filename: str = Query("imagem-produto.jpg")):
    """Baixa uma imagem individual com Content-Disposition attachment para download direto."""
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://shopee.com.br/"
            }
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Erro ao baixar imagem.")
            
            content_type = resp.headers.get("content-type", "image/jpeg")
            return StreamingResponse(
                io.BytesIO(resp.content),
                media_type=content_type,
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"',
                    "Content-Length": str(len(resp.content))
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/proxy-image")
async def proxy_image(url: str = Query(...)):
    """Proxy para exibir imagens da Shopee evitando problemas de cabeçalhos no frontend."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://shopee.com.br/"
            }
            resp = await client.get(url, headers=headers)
            content_type = resp.headers.get("content-type", "image/jpeg")
            return Response(content=resp.content, media_type=content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import socket

def get_local_ip() -> str:
    """Detecta o IP local do computador na rede Wi-Fi/Ethernet."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

@app.get("/api/network-info")
async def get_network_info():
    """Retorna o IP local e URL para acesso por smartphones (Wi-Fi e 4G/5G)."""
    local_ip = get_local_ip()
    pub_url = tunnel.get_public_url()
    return {
        "local_ip": local_ip,
        "port": 8000,
        "local_url": "http://localhost:8000",
        "network_url": f"http://{local_ip}:8000",
        "public_url": pub_url
    }

# Servir arquivos estáticos do frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import sys

    # Força encoding UTF-8 se stdout existir
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    local_ip = get_local_ip()

    def open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    try:
        print("=" * 65)
        print(">> BAIXADOR SHOPEE PRO INICIADO COM SUCESSO!")
        print(f">> No seu computador:          http://localhost:8000")
        print(f">> No celular / outros (Wi-Fi): http://{local_ip}:8000")
        print("=" * 65)
    except Exception:
        pass

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_config=None)
