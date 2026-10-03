import re
import json
import time
import urllib.parse
from typing import Dict, Any, List, Optional, Set
import httpx
from playwright.async_api import async_playwright

IMAGE_CDN_BASE = "https://down-br.img.susercontent.com/file/"
VIDEO_CDN_DOMAINS = [
    "https://cvf.shopee.com.br/file/",
    "https://cv.shopee.com.br/file/",
    "https://down-tx-br.img.susercontent.com/file/"
]

# Padrões para descartar imagens que NÃO são do produto
EXCLUDED_PATTERNS = [
    "avatar", "seller", "shop_logo", "badge", "voucher", "rating", "star", 
    "review", "comment", "logo", "icon", "banner", "payment", "mall-logo",
    "free-shipping", "guarantee", "sp_atk", "100x100", "60x60", "32x32",
    "50x50", "40x40", "20x20", "official", "curated", "user_avatar",
    "btn_", "ic_", "tag_", "shopee_live", "voucher_badge"
]

def clean_filename(title: str, max_length: int = 50) -> str:
    """Gera um nome de arquivo limpo e seguro para Windows."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    clean = re.sub(r'[\s_]+', "-", clean).strip("-")
    if not clean:
        clean = "produto-shopee"
    return clean[:max_length]

def extract_hash_from_str(val: str) -> Optional[str]:
    """Extrai hash de imagem limpo da Shopee."""
    if not val or not isinstance(val, str):
        return None
    
    val = val.strip()
    # Se for URL completa
    if "/file/" in val:
        raw_hash = val.split("/file/")[-1]
        raw_hash = raw_hash.split("?")[0].split("@")[0].split("_tn")[0].split("_m")[0]
        if len(raw_hash) >= 12:
            return raw_hash
    elif not val.startswith("http") and not val.startswith("//") and len(val) >= 12 and "/" not in val:
        # Já é o hash direto (ex: br-11134207-7r98o-xxxxxx ou 32 hex)
        raw_hash = val.split("?")[0].split("@")[0].split("_tn")[0]
        return raw_hash

    return None

def normalize_image_url(val: str) -> Optional[str]:
    """Formata para a URL original da CDN em máxima resolução."""
    if not val:
        return None
    val_lower = val.lower()
    for bad in EXCLUDED_PATTERNS:
        if bad in val_lower:
            return None

    img_hash = extract_hash_from_str(val)
    if img_hash:
        return f"{IMAGE_CDN_BASE}{img_hash}"
    
    if val.startswith("http") and ("susercontent.com" in val or "cf.shopee" in val):
        clean_url = val.split("?")[0].split("@")[0].split("_tn")[0]
        return clean_url

    return None

class ShopeeScraper:
    def __init__(self):
        pass

    async def extract_product_info(self, url: str) -> Dict[str, Any]:
        """Extrai todos os dados de forma ultra-confiável com Playwright e análise multinível."""
        raw_url = url.strip()
        if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
            raw_url = "https://" + raw_url

        intercepted_api_data = {}
        captured_video_urls: Set[str] = set()
        captured_image_hashes: Set[str] = set()
        extracted_dom_data = {}
        script_json_blobs = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certificate-errors",
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900},
                locale="pt-BR",
                timezone_id="America/Sao_Paulo"
            )

            # Injeção anti-detecção
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            page = await context.new_page()

            # 1. INTERCEPTAÇÃO DE REDE EM TEMPO REAL
            async def on_response(response):
                try:
                    resp_url = response.url
                    resp_url_lower = resp_url.lower()
                    content_type = response.headers.get("content-type", "").lower()

                    # Detecção de Vídeo em tráfego de rede
                    if (
                        "video/mp4" in content_type or
                        "video/" in content_type or
                        ".mp4" in resp_url_lower or
                        "cvf.shopee" in resp_url_lower or
                        "cv.shopee" in resp_url_lower or
                        "down-tx-br.img.susercontent.com" in resp_url_lower
                    ):
                        if not resp_url.startswith("blob:") and response.status in [200, 206]:
                            captured_video_urls.add(resp_url)

                    # Detecção de APIs de Produto
                    if any(endpoint in resp_url_lower for endpoint in [
                        "api/v4/pdp/get_pc",
                        "api/v4/item/get",
                        "api/v2/item/get",
                        "api/v4/item/get_item_detail",
                        "api/v4/product/get_pc",
                        "api/v4/batch/get_pdp_info"
                    ]):
                        if response.status == 200:
                            data = await response.json()
                            if isinstance(data, dict):
                                intercepted_api_data["pdp_data"] = data
                except Exception:
                    pass

            page.on("response", on_response)

            try:
                # O Playwright segue tanto redirects HTTP quanto JavaScript client-side
                await page.goto(raw_url, timeout=40000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)

                # Aciona qualquer botão de play/vídeo na área da galeria
                try:
                    video_elements = await page.query_selector_all('video, [class*="play"], [class*="picture-wrapper"], div.flex-box')
                    for el in video_elements[:3]:
                        try:
                            await el.hover(timeout=800)
                        except Exception:
                            pass
                except Exception:
                    pass

                # Rola suavemente para baixo para carregar os blocos de descrição e especificações
                await page.evaluate("window.scrollBy(0, 1000);")
                await page.wait_for_timeout(1500)

                # 2. EXTRAÇÃO DOM E SCRIPTS
                extracted_dom_data = await page.evaluate("""() => {
                    const res = {
                        title: '',
                        description: '',
                        price: '',
                        images: [],
                        video_urls: [],
                        attributes: [],
                        scripts: [],
                        window_state: null
                    };

                    // Título
                    const titleElem = document.querySelector('div._44qnta') || 
                                     document.querySelector('div[class*="product-briefing"] h1') || 
                                     document.querySelector('span[class*="WBVL"]') ||
                                     document.querySelector('h1');
                    if (titleElem) {
                        res.title = titleElem.innerText.trim();
                    } else {
                        res.title = document.title;
                    }

                    // Descrição
                    const descElem = document.querySelector('div.fAInvO') || 
                                     document.querySelector('div[class*="product-detail"]') ||
                                     document.querySelector('p[class*="e8duaR"]') ||
                                     document.querySelector('div.page-product__description');
                    if (descElem) {
                        res.description = descElem.innerText.trim();
                    }

                    // Preço
                    const priceElem = document.querySelector('div.G27FPf') || 
                                      document.querySelector('div[class*="price"]') ||
                                      document.querySelector('div._3n5NQx');
                    if (priceElem) {
                        res.price = priceElem.innerText.trim();
                    }

                    // Vídeos no DOM
                    document.querySelectorAll('video').forEach(v => {
                        if (v.src && !v.src.startsWith('blob:')) res.video_urls.push(v.src);
                        if (v.currentSrc && !v.currentSrc.startsWith('blob:')) res.video_urls.push(v.currentSrc);
                        v.querySelectorAll('source').forEach(s => {
                            if (s.src) res.video_urls.push(s.src);
                        });
                    });

                    // Imagens da Galeria Principal (EXCLUSIVO do produto)
                    const mainContainers = document.querySelectorAll(
                        'div[class*="product-briefing"], div[class*="gallery"], div[class*="carousel"], div[class*="picture-wrapper"]'
                    );
                    mainContainers.forEach(c => {
                        c.querySelectorAll('img').forEach(img => {
                            const src = img.src || img.getAttribute('data-src') || '';
                            if (src && (src.includes('susercontent.com') || src.includes('cf.shopee.com.br'))) {
                                res.images.push(src);
                            }
                        });
                    });

                    // Ficha Técnica / Atributos
                    const attrItems = document.querySelectorAll('div.page-product__details div.flex, div[class*="product-detail"] div.flex');
                    attrItems.forEach(row => {
                        const label = row.querySelector('label') || row.querySelector('span');
                        const val = row.querySelector('div') || row.querySelector('p');
                        if (label && val) {
                            const lText = label.innerText.trim();
                            const vText = val.innerText.trim();
                            if (lText && vText && lText !== vText) {
                                res.attributes.push({ name: lText, value: vText });
                            }
                        }
                    });

                    // Scripts com JSON de dados
                    document.querySelectorAll('script').forEach(s => {
                        const content = s.innerText || s.textContent || '';
                        if (
                            content.includes('video_info_list') || 
                            content.includes('cvf.shopee') || 
                            content.includes('initialState') || 
                            content.includes('item_id') ||
                            content.includes('image_id')
                        ) {
                            res.scripts.push(content);
                        }
                    });

                    // Estado do window se disponível
                    if (window.__INITIAL_STATE__) {
                        try { res.window_state = JSON.stringify(window.__INITIAL_STATE__); } catch(e) {}
                    }

                    return res;
                }""")

                final_resolved_url = page.url
                script_json_blobs = extracted_dom_data.get("scripts", [])
                if extracted_dom_data.get("window_state"):
                    script_json_blobs.append(extracted_dom_data["window_state"])

            except Exception as err:
                print(f"Aviso durante navegação Playwright: {err}")
                final_resolved_url = raw_url
            finally:
                await browser.close()

        # 3. EXTRAÇÃO PROFUNDA DE VÍDEOS DOS SCRIPTS E JSON
        for blob in script_json_blobs:
            # Padrão 1: Links MP4 diretos
            for m in re.findall(r'https?:\\?/\\?/[^\s"\'<>]+\.mp4[^\s"\'<>]*', blob):
                cleaned = m.replace(r'\/', '/').replace('\\u002F', '/')
                captured_video_urls.add(cleaned)

            # Padrão 2: URLs cvf.shopee.com.br
            for m in re.findall(r'https?:\\?/\\?/cvf\.shopee\.com\.br\\?/file\\?/[a-zA-Z0-9_-]+', blob):
                cleaned = m.replace(r'\/', '/').replace('\\u002F', '/')
                captured_video_urls.add(cleaned)

            # Padrão 3: Objetos de vídeo com video_id
            for vid_id in re.findall(r'"video_id"\s*:\s*"([a-zA-Z0-9_-]+)"', blob):
                if vid_id and len(vid_id) >= 10:
                    captured_video_urls.add(f"https://cvf.shopee.com.br/file/{vid_id}")
                    captured_video_urls.add(f"https://down-tx-br.img.susercontent.com/file/{vid_id}")

            # Padrão 4: Hashes de imagem do produto no JSON
            for img_match in re.findall(r'"images"\s*:\s*\[([^\]]+)\]', blob):
                hashes = re.findall(r'"([a-zA-Z0-9_-]+)"', img_match)
                for h in hashes:
                    if len(h) >= 16:
                        captured_image_hashes.add(h)

        # 4. CONSOLIDAÇÃO DOS DADOS
        return self._consolidate_data(
            intercepted_api_data=intercepted_api_data,
            dom_data=extracted_dom_data,
            captured_video_urls=list(captured_video_urls),
            captured_image_hashes=list(captured_image_hashes),
            original_url=raw_url,
            resolved_url=final_resolved_url
        )

    def _consolidate_data(
        self,
        intercepted_api_data: dict,
        dom_data: dict,
        captured_video_urls: List[str],
        captured_image_hashes: List[str],
        original_url: str,
        resolved_url: str
    ) -> Dict[str, Any]:
        
        # Recupera dados da API interceptada se disponíveis
        api_data = intercepted_api_data.get("pdp_data", {})
        item = {}

        if "data" in api_data and isinstance(api_data["data"], dict):
            if "item" in api_data["data"]:
                item = api_data["data"]["item"]
            else:
                item = api_data["data"]
        elif "item" in api_data and isinstance(api_data["item"], dict):
            item = api_data["item"]

        # TÍTULO
        title = item.get("title") or item.get("name") or dom_data.get("title") or "Produto Shopee"
        # Limpar título de sufixos genéricos
        title = re.sub(r'[\r\n\t]+', ' ', title).strip()
        if " | Shopee Brasil" in title:
            title = title.replace(" | Shopee Brasil", "").strip()

        # DESCRIÇÃO
        description = item.get("description") or dom_data.get("description") or ""

        # PREÇO
        raw_price = item.get("price") or item.get("price_min") or 0
        price_str = dom_data.get("price", "")
        if raw_price:
            try:
                price_val = float(raw_price) / 100000.0 if float(raw_price) > 1000 else float(raw_price)
                price_str = f"R$ {price_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            except Exception:
                if not price_str:
                    price_str = str(raw_price)
        
        # RATING E VENDAS
        rating = 5.0
        if "item_rating" in item and isinstance(item["item_rating"], dict):
            rating = round(item["item_rating"].get("rating_star", 5.0), 1)
        elif "rating_star" in item:
            rating = round(float(item.get("rating_star", 5.0)), 1)

        historical_sold = item.get("historical_sold", 0)

        # =====================================================================
        # PROCESSAMENTO EXCLUSIVO DE IMAGENS DO PRODUTO (SEM LIXO)
        # =====================================================================
        product_images: List[str] = []
        seen_hashes: Set[str] = set()

        def register_image(raw_val: str):
            if not raw_val:
                return
            clean_url = normalize_image_url(raw_val)
            if clean_url:
                h = extract_hash_from_str(clean_url)
                if h and h not in seen_hashes:
                    seen_hashes.add(h)
                    product_images.append(clean_url)

        # 1. Imagens Oficiais da API Shopee
        for img in item.get("images", []):
            register_image(img)

        # 2. Imagens das Variações / Modelos
        for m in item.get("models", []):
            if isinstance(m, dict) and m.get("image"):
                register_image(m["image"])

        for tv in item.get("tier_variations", []):
            if isinstance(tv, dict) and isinstance(tv.get("images"), list):
                for img in tv["images"]:
                    register_image(img)

        # 3. Hashes extraídos dos JSONs da página
        for h in captured_image_hashes:
            register_image(h)

        # 4. Imagens da Galeria Principal do DOM (caso a API não tenha retornado)
        if len(product_images) == 0:
            for d_img in dom_data.get("images", []):
                register_image(d_img)

        cover_image = product_images[0] if product_images else ""

        # =====================================================================
        # PROCESSAMENTO DE VÍDEO DO PRODUTO (SEM MARCA D'ÁGUA / HD ORIGINAL)
        # =====================================================================
        ranked_videos = []

        def sanitize_clean_video_url(raw_url: str) -> str:
            """Remove parâmetros de marca d'água e overlay da URL do vídeo."""
            if not raw_url:
                return ""
            clean_u = raw_url.strip().replace(r'\/', '/').replace('\\u002F', '')
            try:
                parsed = urllib.parse.urlparse(clean_u)
                qs = urllib.parse.parse_qs(parsed.query)
                # Remove parâmetros de marca d'água se existirem
                for wm_key in ["watermark", "wm", "logo", "watermark_type", "has_watermark"]:
                    qs.pop(wm_key, None)
                new_query = urllib.parse.urlencode(qs, doseq=True)
                clean_u = urllib.parse.urlunparse((
                    parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment
                ))
            except Exception:
                pass
            return clean_u

        def add_format_candidate(url, width=0, height=0, bitrate=0, fmt_id=0, source="api", is_clean=True):
            if not url or not isinstance(url, str) or url.startswith("blob:"):
                return
            clean_u = sanitize_clean_video_url(url)
            if not clean_u.startswith("http"):
                return

            w = int(width or 0)
            h = int(height or 0)
            br = int(bitrate or 0)
            area = w * h

            # Se não tem resolução explícita, deduz por padrões da CDN
            if area == 0:
                if "1080" in clean_u:
                    area = 1080 * 1920
                elif "720" in clean_u:
                    area = 720 * 1280
                elif "540" in clean_u:
                    area = 540 * 960
                elif "360" in clean_u:
                    area = 360 * 640
                elif "format=100" in clean_u or "/100/" in clean_u:
                    area = 1080 * 1920
                else:
                    area = 720 * 1280

            score = (area * 10) + br
            if ".mp4" in clean_u.lower():
                score += 50000
            # Prioriza master MMS original (que é 100% sem marca d'água)
            if "/mms/" in clean_u or "cvf.shopee" in clean_u or "down-tx-br" in clean_u:
                score += 40000
            if source.startswith("api"):
                score += 20000
            if is_clean:
                score += 30000

            ranked_videos.append({
                "url": clean_u,
                "score": score,
                "width": w,
                "height": h,
                "bitrate": br
            })

        # 1. Analisa todos os formatos disponíveis na API
        for v in item.get("video_info_list", []):
            if isinstance(v, dict):
                # Verifica URLs diretas sem marca d'água se existirem
                for clean_field in ["watermark_free_url", "no_watermark_url", "clean_url", "origin_url", "master_url"]:
                    if v.get(clean_field):
                        add_format_candidate(v[clean_field], width=1080, height=1920, source="api_clean", is_clean=True)

                # formats (geralmente contém todas as qualidades: 1080p, 720p, etc.)
                for fmt in v.get("formats", []):
                    if isinstance(fmt, dict) and fmt.get("url"):
                        add_format_candidate(
                            url=fmt["url"],
                            width=fmt.get("width", 0),
                            height=fmt.get("height", 0),
                            bitrate=fmt.get("bitrate", 0),
                            fmt_id=fmt.get("format", 0),
                            source="api_formats",
                            is_clean=True
                        )
                # default_format
                def_fmt = v.get("default_format", {})
                if isinstance(def_fmt, dict) and def_fmt.get("url"):
                    add_format_candidate(
                        url=def_fmt["url"],
                        width=def_fmt.get("width", 0),
                        height=def_fmt.get("height", 0),
                        bitrate=def_fmt.get("bitrate", 0),
                        fmt_id=def_fmt.get("format", 0),
                        source="api_default",
                        is_clean=True
                    )

        # 2. Vídeos capturados na rede (requests master .mp4)
        for net_v in captured_video_urls:
            add_format_candidate(net_v, source="network", is_clean=True)

        # 3. Vídeos do DOM
        for dom_v in dom_data.get("video_urls", []):
            add_format_candidate(dom_v, source="dom")

        # Ordena pelo maior score de resolução e pureza do stream
        ranked_videos.sort(key=lambda x: x["score"], reverse=True)

        # Deduplica preservando a ordem da melhor qualidade sem marca d'água
        product_videos: List[str] = []
        seen_v_urls: Set[str] = set()
        for cand in ranked_videos:
            u = cand["url"]
            if u not in seen_v_urls:
                seen_v_urls.add(u)
                product_videos.append(u)

        # ESPECIFICAÇÕES
        attributes = []
        for a in item.get("attributes", []):
            name = a.get("name") or a.get("key", "")
            val = a.get("value", "")
            if name and val:
                attributes.append({"name": str(name), "value": str(val)})

        if not attributes and dom_data.get("attributes"):
            attributes = dom_data.get("attributes")

        filename_base = clean_filename(title)

        return {
            "success": True,
            "title": title,
            "filename_base": filename_base,
            "description": description,
            "price": price_str,
            "rating": rating,
            "sales_count": historical_sold,
            "cover_image": cover_image,
            "images": product_images,
            "image_count": len(product_images),
            "videos": product_videos,
            "video_count": len(product_videos),
            "has_video": len(product_videos) > 0,
            "attributes": attributes,
            "original_url": original_url,
            "resolved_url": resolved_url
        }
