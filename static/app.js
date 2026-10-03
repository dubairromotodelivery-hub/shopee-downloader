// Estado da aplicação
let currentProduct = null;
let historyItems = JSON.parse(localStorage.getItem('shopee_downloader_history') || '[]');

// Elementos DOM
const extractForm = document.getElementById('extractForm');
const urlInput = document.getElementById('urlInput');
const btnClear = document.getElementById('btnClear');
const btnPaste = document.getElementById('btnPaste');
const btnSubmit = document.getElementById('btnSubmit');
const btnText = document.getElementById('btnText');
const btnIcon = document.getElementById('btnIcon');
const btnSpinner = document.getElementById('btnSpinner');

const statusCard = document.getElementById('statusCard');
const statusText = document.getElementById('statusText');
const errorCard = document.getElementById('errorCard');
const errorMessage = document.getElementById('errorMessage');
const btnCloseError = document.getElementById('btnCloseError');

const productShowcase = document.getElementById('productShowcase');
const productCover = document.getElementById('productCover');
const videoBadge = document.getElementById('videoBadge');
const priceBadge = document.getElementById('priceBadge');
const ratingBox = document.getElementById('ratingBox');
const ratingVal = document.getElementById('ratingVal');
const salesBadge = document.getElementById('salesBadge');
const productTitle = document.getElementById('productTitle');

const statImages = document.getElementById('statImages');
const statVideo = document.getElementById('statVideo');
const statDesc = document.getElementById('statDesc');

// Botões principais de Download
const btnDownloadVideo = document.getElementById('btnDownloadVideo');
const btnDownloadImages = document.getElementById('btnDownloadImages');
const btnDownloadDescriptionTxt = document.getElementById('btnDownloadDescriptionTxt');
const btnDownloadAll = document.getElementById('btnDownloadAll');

// Tabs
const tabButtons = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-panel');
const tabCountImages = document.getElementById('tabCountImages');
const tabBadgeVideo = document.getElementById('tabBadgeVideo');

// Painéis de Conteúdo
const imageGalleryGrid = document.getElementById('imageGalleryGrid');
const btnQuickImages = document.getElementById('btnQuickImages');
const videoContainer = document.getElementById('videoContainer');
const noVideoMsg = document.getElementById('noVideoMsg');

const descriptionText = document.getElementById('descriptionText');
const btnCopyDesc = document.getElementById('btnCopyDesc');
const btnCopyText = document.getElementById('btnCopyText');
const btnDownloadDescTxtTab = document.getElementById('btnDownloadDescTxtTab');
const attributesSection = document.getElementById('attributesSection');
const attributesGrid = document.getElementById('attributesGrid');

// Modais
const historyModal = document.getElementById('historyModal');
const btnOpenHistory = document.getElementById('btnOpenHistory');
const btnCloseHistory = document.getElementById('btnCloseHistory');
const btnClearHistory = document.getElementById('btnClearHistory');
const historyList = document.getElementById('historyList');
const historyBadge = document.getElementById('historyBadge');

const lightboxModal = document.getElementById('lightboxModal');
const lightboxImg = document.getElementById('lightboxImg');
const lightboxDownloadBtn = document.getElementById('lightboxDownloadBtn');
const btnCloseLightbox = document.getElementById('btnCloseLightbox');

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    updateHistoryBadge();
    setupEventListeners();
});

function setupEventListeners() {
    // Input changes
    urlInput.addEventListener('input', () => {
        if (urlInput.value.trim().length > 0) {
            btnClear.classList.remove('hidden');
        } else {
            btnClear.classList.add('hidden');
        }
    });

    // Limpar input
    btnClear.addEventListener('click', () => {
        urlInput.value = '';
        btnClear.classList.add('hidden');
        urlInput.focus();
    });

    // Colar da área de transferência
    btnPaste.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                btnClear.classList.remove('hidden');
                if (text.includes('shopee.com') || text.includes('shp.ee') || text.includes('shope.ee')) {
                    extractForm.dispatchEvent(new Event('submit'));
                }
            }
        } catch (err) {
            console.warn('Não foi possível acessar a área de transferência', err);
        }
    });

    // Submissão do Formulário
    extractForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;
        await processExtract(url);
    });

    // Fechar erro
    btnCloseError.addEventListener('click', () => {
        errorCard.classList.add('hidden');
    });

    // Alternar Tabs
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            
            tabButtons.forEach(b => {
                b.classList.remove('active', 'border-orange-500', 'text-orange-400');
                b.classList.add('border-transparent', 'text-slate-400');
            });
            btn.classList.add('active', 'border-orange-500', 'text-orange-400');
            btn.classList.remove('border-transparent', 'text-slate-400');

            tabPanels.forEach(p => {
                if (p.id === targetId) {
                    p.classList.remove('hidden');
                } else {
                    p.classList.add('hidden');
                }
            });
            lucide.createIcons();
        });
    });

    // 1. Botão Baixar Vídeo (MP4)
    btnDownloadVideo.addEventListener('click', () => downloadProductVideo());

    // 2. Botão Baixar Imagens (Normalmente, sem ZIP)
    if (btnDownloadImages) {
        btnDownloadImages.addEventListener('click', () => downloadAllImagesNormally());
    }
    if (btnQuickImages) {
        btnQuickImages.addEventListener('click', () => downloadAllImagesNormally());
    }

    // 3. Botão Baixar Descrição (.txt)
    btnDownloadDescriptionTxt.addEventListener('click', () => downloadDescriptionTxt());
    btnDownloadDescTxtTab.addEventListener('click', () => downloadDescriptionTxt());

    // 4. Botão Baixar Tudo (Vídeo + Imagens normais + Descrição)
    if (btnDownloadAll) {
        btnDownloadAll.addEventListener('click', () => downloadAllMediaTogether());
    }

    // Copiar descrição
    btnCopyDesc.addEventListener('click', async () => {
        if (!currentProduct) return;
        let fullTxt = `PRODUTO: ${currentProduct.title}\nPREÇO: ${currentProduct.price}\nLINK: ${currentProduct.original_url}\n\n`;
        if (currentProduct.attributes && currentProduct.attributes.length > 0) {
            fullTxt += `ESPECIFICAÇÕES:\n`;
            currentProduct.attributes.forEach(a => {
                fullTxt += `• ${a.name}: ${a.value}\n`;
            });
            fullTxt += `\n`;
        }
        fullTxt += `DESCRIÇÃO:\n${currentProduct.description}`;

        try {
            await navigator.clipboard.writeText(fullTxt);
            btnCopyText.innerText = 'Copiado com Sucesso!';
            btnCopyDesc.classList.add('bg-emerald-600', 'border-emerald-500', 'text-white');
            setTimeout(() => {
                btnCopyText.innerText = 'Copiar Texto';
                btnCopyDesc.classList.remove('bg-emerald-600', 'border-emerald-500', 'text-white');
            }, 2500);
        } catch (err) {
            console.error('Falha ao copiar:', err);
        }
    });

    // Modais
    btnOpenHistory.addEventListener('click', () => {
        renderHistory();
        historyModal.classList.remove('hidden');
    });

    btnCloseHistory.addEventListener('click', () => {
        historyModal.classList.add('hidden');
    });

    btnClearHistory.addEventListener('click', () => {
        historyItems = [];
        localStorage.removeItem('shopee_downloader_history');
        renderHistory();
        updateHistoryBadge();
    });

    btnCloseLightbox.addEventListener('click', () => {
        lightboxModal.classList.add('hidden');
    });

    lightboxModal.addEventListener('click', (e) => {
        if (e.target === lightboxModal) {
            lightboxModal.classList.add('hidden');
        }
    });
}

// Processa a Extração
async function processExtract(url) {
    setLoadingState(true);
    errorCard.classList.add('hidden');
    productShowcase.classList.add('hidden');

    try {
        const response = await fetch('/api/extract', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.detail || 'Não foi possível extrair os dados do anúncio.');
        }

        currentProduct = data;
        renderProductData(data);
        saveToHistory(data);
    } catch (err) {
        console.error('Erro na extração:', err);
        errorMessage.innerText = err.message || 'Falha ao conectar e extrair dados da Shopee. Verifique o link e tente novamente.';
        errorCard.classList.remove('hidden');
    } finally {
        setLoadingState(false);
    }
}

// Renderiza os dados do produto no DOM
function renderProductData(data) {
    productTitle.innerText = data.title;
    productCover.src = data.cover_image || (data.images[0] || '');
    priceBadge.innerText = data.price || 'Preço indisponível';

    if (data.rating > 0) {
        ratingVal.innerText = data.rating.toFixed(1);
        ratingBox.classList.remove('hidden');
    } else {
        ratingBox.classList.add('hidden');
    }

    salesBadge.innerText = `${data.sales_count.toLocaleString('pt-BR')} vendidos`;

    // Estatísticas resumidas
    statImages.innerText = `${data.image_count} Fotos encontradas`;
    tabCountImages.innerText = data.image_count;

    if (data.has_video) {
        statVideo.innerText = `${data.video_count} Vídeo disponível (HD)`;
        videoBadge.classList.remove('hidden');
        tabBadgeVideo.innerText = '1';
        btnDownloadVideo.removeAttribute('disabled');
        btnDownloadVideo.classList.remove('opacity-40', 'cursor-not-allowed');
    } else {
        statVideo.innerText = 'Nenhum vídeo neste anúncio';
        videoBadge.classList.add('hidden');
        tabBadgeVideo.innerText = '0';
        btnDownloadVideo.setAttribute('disabled', 'true');
        btnDownloadVideo.classList.add('opacity-40', 'cursor-not-allowed');
    }

    // 1. Galeria de Imagens
    renderGallery(data.images, data.title);

    // 2. Vídeo Player
    renderVideoPlayer(data.videos, data.cover_image, data.title);

    // 3. Descrição & Atributos
    renderDescription(data.description, data.attributes);

    // Exibe o painel principal
    productShowcase.classList.remove('hidden');
    lucide.createIcons();

    // Rola até o resultado
    productShowcase.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Renderiza a galeria de imagens
function renderGallery(images, title) {
    imageGalleryGrid.innerHTML = '';
    if (!images || images.length === 0) {
        imageGalleryGrid.innerHTML = `<p class="col-span-full text-center text-slate-500 py-6 text-sm">Nenhuma foto encontrada.</p>`;
        return;
    }

    images.forEach((imgUrl, index) => {
        const card = document.createElement('div');
        card.className = 'gallery-card relative group rounded-xl overflow-hidden bg-slate-900 border border-slate-800 aspect-square';

        const downloadSingleUrl = `/api/download/single-image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(currentProduct.filename_base + '-foto-' + (index + 1) + '.jpg')}`;

        card.innerHTML = `
            <img src="${imgUrl}" alt="Foto ${index + 1}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy">
            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-between p-2.5">
                <button class="btn-zoom text-white/90 hover:text-white bg-slate-800/80 hover:bg-slate-700 p-1.5 rounded-lg text-xs" title="Visualizar em tamanho grande">
                    <i data-lucide="zoom-in" class="w-4 h-4"></i>
                </button>
                <a href="${downloadSingleUrl}" class="bg-orange-500 hover:bg-orange-600 text-white p-1.5 rounded-lg text-xs font-medium flex items-center gap-1 shadow-md" title="Baixar foto individual">
                    <i data-lucide="download" class="w-4 h-4"></i>
                </a>
            </div>
            <span class="absolute top-2 left-2 bg-slate-950/70 backdrop-blur-md text-[10px] font-bold text-slate-300 px-1.5 py-0.5 rounded">#${index + 1}</span>
        `;

        card.querySelector('.btn-zoom').addEventListener('click', () => {
            openLightbox(imgUrl);
        });

        imageGalleryGrid.appendChild(card);
    });
}

// Renderiza o player de vídeo
function renderVideoPlayer(videos, poster, title) {
    if (videos && videos.length > 0) {
        const videoUrl = videos[0];
        videoContainer.innerHTML = `
            <div class="relative rounded-2xl overflow-hidden bg-black border border-slate-800 shadow-2xl">
                <video controls playsinline poster="${poster}" class="w-full max-h-[480px] object-contain">
                    <source src="${videoUrl}" type="video/mp4">
                    Seu navegador não suporta reprodução de vídeo HTML5.
                </video>
                <div class="absolute top-3 left-3 bg-slate-950/80 backdrop-blur-md text-emerald-400 border border-emerald-500/30 text-[11px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1.5 shadow-md">
                    <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                    <span>SEM MARCA D'ÁGUA • ORIGINAL</span>
                </div>
            </div>
            <div class="mt-4 flex items-center justify-center gap-3">
                <button id="btnPlayerDownloadVideo" class="bg-gradient-to-r from-red-600 to-rose-600 hover:from-red-500 hover:to-rose-500 text-white font-semibold px-6 py-3 rounded-xl text-sm flex items-center gap-2 shadow-glow transition-all">
                    <i data-lucide="download" class="w-4 h-4"></i>
                    Baixar Vídeo Sem Marca d'Água (MP4)
                </button>
            </div>
        `;
        videoContainer.classList.remove('hidden');
        noVideoMsg.classList.add('hidden');

        document.getElementById('btnPlayerDownloadVideo').addEventListener('click', () => {
            downloadProductVideo();
        });
    } else {
        videoContainer.innerHTML = '';
        videoContainer.classList.add('hidden');
        noVideoMsg.classList.remove('hidden');
    }
}

// Renderiza descrição e atributos
function renderDescription(desc, attributes) {
    descriptionText.innerText = desc || 'Sem descrição detalhada para este produto.';

    if (attributes && attributes.length > 0) {
        attributesGrid.innerHTML = '';
        attributes.forEach(attr => {
            const item = document.createElement('div');
            item.className = 'bg-slate-900/80 p-3 rounded-xl border border-slate-800/80 flex flex-col';
            item.innerHTML = `
                <span class="text-[11px] font-medium text-slate-400 uppercase tracking-wider">${escapeHtml(attr.name)}</span>
                <span class="text-xs font-semibold text-slate-200 mt-0.5">${escapeHtml(attr.value)}</span>
            `;
            attributesGrid.appendChild(item);
        });
        attributesSection.classList.remove('hidden');
    } else {
        attributesSection.classList.add('hidden');
    }
}

// =========================================================================
// FUNÇÕES DE DOWNLOAD (100% FUNCIONAIS E DIRETAS)
// =========================================================================

// 1. BAIXAR VÍDEO (MP4) - SEM ABRIR ABAS, DOWNLOAD DIRETO
async function downloadProductVideo() {
    if (!currentProduct || !currentProduct.videos || currentProduct.videos.length === 0) {
        alert('Este produto não possui vídeo disponível.');
        return;
    }

    const originalHtml = btnDownloadVideo.innerHTML;
    btnDownloadVideo.innerHTML = `<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div><span>Baixando vídeo...</span>`;
    btnDownloadVideo.setAttribute('disabled', 'true');

    const filename = `${currentProduct.filename_base}-video.mp4`;
    let downloaded = false;

    // 1. Tenta baixar via backend para cada URL de vídeo disponível até funcionar
    for (const videoUrl of currentProduct.videos) {
        try {
            const downloadUrl = `/api/download/video?video_url=${encodeURIComponent(videoUrl)}&title=${encodeURIComponent(currentProduct.title)}`;
            const resp = await fetch(downloadUrl);
            if (resp.ok) {
                const blob = await resp.blob();
                if (blob.size > 1000) {
                    downloadBlob(blob, filename);
                    downloaded = true;
                    break;
                }
            }
        } catch (err) {
            console.warn('Tentativa via servidor falhou para URL:', videoUrl, err);
        }
    }

    // 2. Se o backend não conseguiu, tenta download direto via fetch no navegador
    if (!downloaded && currentProduct.videos.length > 0) {
        for (const videoUrl of currentProduct.videos) {
            try {
                const resp2 = await fetch(videoUrl);
                if (resp2.ok) {
                    const blob2 = await resp2.blob();
                    if (blob2.size > 1000) {
                        downloadBlob(blob2, filename);
                        downloaded = true;
                        break;
                    }
                }
            } catch (e2) {
                console.warn('Fetch direto no cliente falhou:', videoUrl, e2);
            }
        }
    }

    // 3. Fallback: aciona o endpoint de download direto no mesmo documento (sem _blank)
    if (!downloaded && currentProduct.videos.length > 0) {
        const directUrl = `/api/download/video?video_url=${encodeURIComponent(currentProduct.videos[0])}&title=${encodeURIComponent(currentProduct.title)}`;
        const a = document.createElement('a');
        a.href = directUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    btnDownloadVideo.innerHTML = originalHtml;
    btnDownloadVideo.removeAttribute('disabled');
    lucide.createIcons();
}

// 2. BAIXAR IMAGENS NORMALMENTE (SEM ZIP - 1 A 1 DIRETO NA PASTA DE DOWNLOADS)
async function downloadAllImagesNormally() {
    if (!currentProduct || !currentProduct.images || currentProduct.images.length === 0) {
        alert('Nenhuma imagem disponível para baixar.');
        return;
    }

    const total = currentProduct.images.length;
    const originalText = btnDownloadImages ? btnDownloadImages.innerHTML : '';
    
    if (btnDownloadImages) {
        btnDownloadImages.setAttribute('disabled', 'true');
    }

    for (let i = 0; i < total; i++) {
        const imgUrl = currentProduct.images[i];
        const filename = `${currentProduct.filename_base}-foto-${i + 1}.jpg`;
        const downloadUrl = `/api/download/single-image?url=${encodeURIComponent(imgUrl)}&filename=${encodeURIComponent(filename)}`;

        if (btnDownloadImages) {
            btnDownloadImages.innerHTML = `<div class="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div><span>Baixando ${i + 1}/${total}...</span>`;
        }

        try {
            // Cria link de download e aciona
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (e) {
            console.error('Erro ao baixar foto', i + 1, e);
        }

        // Pequeno intervalo entre downloads para o navegador salvar ordenadamente
        await new Promise(r => setTimeout(r, 220));
    }

    if (btnDownloadImages) {
        btnDownloadImages.innerHTML = `<i data-lucide="check" class="w-4 h-4 text-emerald-300"></i><span>${total} Fotos Baixadas!</span>`;
        lucide.createIcons();
        setTimeout(() => {
            btnDownloadImages.innerHTML = originalText;
            btnDownloadImages.removeAttribute('disabled');
            lucide.createIcons();
        }, 3000);
    }
}

// 3. BAIXAR DESCRIÇÃO (.TXT)
async function downloadDescriptionTxt() {
    if (!currentProduct) return;
    try {
        const resp = await fetch('/api/download/description-txt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: currentProduct.title,
                price: currentProduct.price,
                original_url: currentProduct.original_url,
                description: currentProduct.description,
                attributes: currentProduct.attributes || []
            })
        });
        if (!resp.ok) throw new Error('Falha ao gerar arquivo TXT.');
        const blob = await resp.blob();
        downloadBlob(blob, `${currentProduct.filename_base}-descricao.txt`);
    } catch (err) {
        alert('Erro ao baixar descrição: ' + err.message);
    }
}

// 4. BAIXAR TUDO (VÍDEO + TODAS AS FOTOS NORMAIS + DESCRIÇÃO)
async function downloadAllMediaTogether() {
    if (!currentProduct) return;
    
    // 1. Baixar Descrição
    await downloadDescriptionTxt();
    await new Promise(r => setTimeout(r, 300));

    // 2. Baixar Vídeo se houver
    if (currentProduct.has_video) {
        await downloadProductVideo();
        await new Promise(r => setTimeout(r, 300));
    }

    // 3. Baixar Todas as Fotos Normalmente
    await downloadAllImagesNormally();
}

// Helpers de Download
function triggerDirectDownload(url, filename) {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }, 2000);
}

// Lightbox
function openLightbox(url) {
    lightboxImg.src = url;
    const fname = `${currentProduct ? currentProduct.filename_base : 'shopee'}-foto-original.jpg`;
    lightboxDownloadBtn.href = `/api/download/single-image?url=${encodeURIComponent(url)}&filename=${encodeURIComponent(fname)}`;
    lightboxModal.classList.remove('hidden');
    lucide.createIcons();
}

// Histórico
function saveToHistory(product) {
    historyItems = historyItems.filter(item => item.original_url !== product.original_url && item.title !== product.title);
    historyItems.unshift({
        title: product.title,
        cover_image: product.cover_image,
        price: product.price,
        original_url: product.original_url,
        has_video: product.has_video,
        image_count: product.image_count,
        timestamp: new Date().toLocaleDateString('pt-BR', { hour: '2-digit', minute: '2-digit' }),
        data: product
    });

    if (historyItems.length > 20) {
        historyItems.pop();
    }

    localStorage.setItem('shopee_downloader_history', JSON.stringify(historyItems));
    updateHistoryBadge();
}

function updateHistoryBadge() {
    if (historyItems.length > 0) {
        historyBadge.innerText = historyItems.length;
        historyBadge.classList.remove('hidden');
    } else {
        historyBadge.classList.add('hidden');
    }
}

function renderHistory() {
    if (historyItems.length === 0) {
        historyList.innerHTML = `<p class="text-center text-slate-500 py-8 text-xs">Nenhum produto baixado recentemente.</p>`;
        return;
    }

    historyList.innerHTML = '';
    historyItems.forEach((item, idx) => {
        const div = document.createElement('div');
        div.className = 'p-3 flex items-center justify-between gap-3 hover:bg-slate-900/60 rounded-xl transition-colors cursor-pointer group';
        div.innerHTML = `
            <div class="flex items-center gap-3 min-w-0">
                <img src="${item.cover_image}" class="w-12 h-12 rounded-lg object-cover bg-slate-900 shrink-0 border border-slate-800">
                <div class="min-w-0">
                    <h5 class="text-xs font-semibold text-slate-200 line-clamp-1 group-hover:text-orange-400 transition-colors">${escapeHtml(item.title)}</h5>
                    <div class="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
                        <span class="text-orange-400 font-bold">${item.price || ''}</span>
                        <span>•</span>
                        <span>${item.image_count} fotos</span>
                        ${item.has_video ? '<span class="text-red-400">• Vídeo</span>' : ''}
                    </div>
                </div>
            </div>
            <button class="p-2 text-slate-400 hover:text-white bg-slate-800 rounded-lg text-xs shrink-0 group-hover:bg-orange-500 group-hover:text-white transition-colors">
                <i data-lucide="arrow-right" class="w-4 h-4"></i>
            </button>
        `;

        div.addEventListener('click', () => {
            currentProduct = item.data;
            urlInput.value = item.original_url;
            btnClear.classList.remove('hidden');
            renderProductData(item.data);
            historyModal.classList.add('hidden');
        });

        historyList.appendChild(div);
    });
    lucide.createIcons();
}

// Utilitários
function setLoadingState(loading) {
    if (loading) {
        btnSubmit.setAttribute('disabled', 'true');
        btnText.innerText = 'Processando...';
        btnIcon.classList.add('hidden');
        btnSpinner.classList.remove('hidden');
        statusCard.classList.remove('hidden');
    } else {
        btnSubmit.removeAttribute('disabled');
        btnText.innerText = 'Extrair Mídias';
        btnIcon.classList.remove('hidden');
        btnSpinner.classList.add('hidden');
        statusCard.classList.add('hidden');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// =========================================================================
// PWA (INSTALAÇÃO NO COMPUTADOR E CELULAR) E CONEXÃO POR QR CODE
// =========================================================================

// Registra Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(err => console.log('SW registration error:', err));
    });
}

// Captura evento de instalação PWA
let deferredPrompt = null;
const btnInstallApp = document.getElementById('btnInstallApp');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    if (btnInstallApp) {
        btnInstallApp.classList.remove('hidden');
    }
});

if (btnInstallApp) {
    btnInstallApp.addEventListener('click', async () => {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                btnInstallApp.classList.add('hidden');
            }
            deferredPrompt = null;
        } else {
            alert('Para instalar:\n• No Chrome/Edge: Clique no ícone de instalar na barra de endereços.\n• No celular: Escolha "Adicionar à tela inicial" nas opções do navegador.');
        }
    });
}

// Modal Celular & Amigos (QR Code com 4G/5G e Wi-Fi)
const mobileModal = document.getElementById('mobileModal');
const btnOpenMobileModal = document.getElementById('btnOpenMobileModal');
const btnCloseMobileModal = document.getElementById('btnCloseMobileModal');
const qrcodeContainer = document.getElementById('qrcodeContainer');
const mobileNetworkUrl = document.getElementById('mobileNetworkUrl');
const mobileUrlLabel = document.getElementById('mobileUrlLabel');
const btnCopyNetworkUrl = document.getElementById('btnCopyNetworkUrl');
const tab4g = document.getElementById('tab4g');
const tabWifi = document.getElementById('tabWifi');

let qrcodeObj = null;
let networkData = {
    public_url: null,
    network_url: null,
    local_url: 'http://localhost:8000'
};
let currentModalMode = '4g'; // '4g' ou 'wifi'

function renderQrCodeForUrl(targetUrl) {
    if (!targetUrl) return;
    if (mobileNetworkUrl) {
        mobileNetworkUrl.innerText = targetUrl;
    }
    if (qrcodeContainer && window.QRCode) {
        qrcodeContainer.innerHTML = '';
        qrcodeObj = new QRCode(qrcodeContainer, {
            text: targetUrl,
            width: 170,
            height: 170,
            colorDark: "#0F172A",
            colorLight: "#FFFFFF",
            correctLevel: QRCode.CorrectLevel.M
        });
    }
}

function updateModalTabUI(mode) {
    currentModalMode = mode;
    if (mode === '4g') {
        tab4g.className = 'flex-1 py-2 rounded-lg bg-orange-500 text-white shadow-sm flex items-center justify-center gap-1.5 transition-all';
        tabWifi.className = 'flex-1 py-2 rounded-lg text-slate-400 hover:text-slate-200 flex items-center justify-center gap-1.5 transition-all';
        if (mobileUrlLabel) {
            mobileUrlLabel.innerHTML = `<i data-lucide="globe" class="w-3 h-3 text-orange-400"></i> <span class="text-orange-400">Link Seguro HTTPS (4G/5G/Mundo)</span>`;
        }
        const activeUrl = networkData.public_url || networkData.network_url || window.location.origin;
        renderQrCodeForUrl(activeUrl);
    } else {
        tabWifi.className = 'flex-1 py-2 rounded-lg bg-orange-500 text-white shadow-sm flex items-center justify-center gap-1.5 transition-all';
        tab4g.className = 'flex-1 py-2 rounded-lg text-slate-400 hover:text-slate-200 flex items-center justify-center gap-1.5 transition-all';
        if (mobileUrlLabel) {
            mobileUrlLabel.innerHTML = `<i data-lucide="wifi" class="w-3 h-3 text-blue-400"></i> <span class="text-blue-400">Link Rede Local (Mesmo Wi-Fi)</span>`;
        }
        const activeUrl = networkData.network_url || window.location.origin;
        renderQrCodeForUrl(activeUrl);
    }
    lucide.createIcons();
}

if (tab4g) {
    tab4g.addEventListener('click', () => updateModalTabUI('4g'));
}
if (tabWifi) {
    tabWifi.addEventListener('click', () => updateModalTabUI('wifi'));
}

if (btnOpenMobileModal) {
    btnOpenMobileModal.addEventListener('click', async () => {
        try {
            const resp = await fetch('/api/network-info');
            networkData = await resp.json();
            
            // Prefer public_url if available, else network_url
            if (networkData.public_url) {
                updateModalTabUI('4g');
            } else {
                updateModalTabUI('wifi');
            }

            mobileModal.classList.remove('hidden');
            lucide.createIcons();
        } catch (err) {
            console.error('Erro ao buscar dados de rede:', err);
            renderQrCodeForUrl(window.location.origin);
            mobileModal.classList.remove('hidden');
        }
    });
}

if (btnCloseMobileModal) {
    btnCloseMobileModal.addEventListener('click', () => {
        mobileModal.classList.add('hidden');
    });
}

if (mobileModal) {
    mobileModal.addEventListener('click', (e) => {
        if (e.target === mobileModal) {
            mobileModal.classList.add('hidden');
        }
    });
}

if (btnCopyNetworkUrl) {
    btnCopyNetworkUrl.addEventListener('click', async () => {
        const textToCopy = mobileNetworkUrl ? mobileNetworkUrl.innerText : window.location.origin;
        try {
            await navigator.clipboard.writeText(textToCopy);
            btnCopyNetworkUrl.innerText = 'Copiado!';
            btnCopyNetworkUrl.classList.remove('bg-orange-600', 'hover:bg-orange-500');
            btnCopyNetworkUrl.classList.add('bg-emerald-600', 'text-white');
            setTimeout(() => {
                btnCopyNetworkUrl.innerText = 'Copiar';
                btnCopyNetworkUrl.classList.remove('bg-emerald-600', 'text-white');
                btnCopyNetworkUrl.classList.add('bg-orange-600', 'hover:bg-orange-500');
            }, 2000);
        } catch (e) {
            console.error('Erro ao copiar URL:', e);
        }
    });
}
