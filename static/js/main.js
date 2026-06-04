document.addEventListener("DOMContentLoaded", function() {
    
    // =========================================================================
    // 1. MENU LATERAL (GLOBAL - Roda em todas as páginas)
    // =========================================================================
    const btnMenu = document.getElementById('btn-menu');
    const sidebar = document.querySelector('aside');
    const overlay = document.getElementById('menu-overlay');

    // Só ativa os eventos se os elementos do menu existirem na página atual
    if (btnMenu && sidebar && overlay) {
        function toggleMenu() {
            sidebar.classList.toggle('menu-aberto');
            overlay.classList.toggle('menu-aberto');
            
            const isExpanded = btnMenu.getAttribute('aria-expanded') === 'true';
            btnMenu.setAttribute('aria-expanded', !isExpanded);
        }

        btnMenu.addEventListener('click', toggleMenu);
        overlay.addEventListener('click', toggleMenu);
    }

    // =========================================================================
    // 2. LÓGICA DOS MAPAS (CONDICIONAL - Só age nos elementos que existirem)
    // =========================================================================
    const selectAno = document.getElementById("ano-select");
    const container2022 = document.getElementById('container-mapa-2022');
    const container2025 = document.getElementById('container-mapa-2025');
    const containerInternet2025 = document.getElementById('container-mapa-net-cel-2025');

    // Se o dropdown de seleção existir na página, ativa a lógica de troca
    if (selectAno) {
        selectAno.addEventListener('change', function() {
            const valorSelecionado = this.value;

            // Esconde o mapa de 2022 (se ele existir nesta página)
            if (container2022) {
                container2022.style.display = (valorSelecionado === '2022') ? 'block' : 'none';
                container2022.style.height = (valorSelecionado === '2022') ? '100%' : '0';
                container2022.style.overflow = (valorSelecionado === '2022') ? 'visible' : 'hidden';
            }

            // Esconde/Mostra o mapa de população 2025 (se ele existir nesta página)
            if (container2025) {
                container2025.style.display = (valorSelecionado === '2025') ? 'block' : 'none';
                container2025.style.height = (valorSelecionado === '2025') ? '100%' : '0';
                container2025.style.overflow = (valorSelecionado === '2025') ? 'visible' : 'hidden';
            }

            // ESPECÍFICO DE TIC_PSR: Só manipula o mapa de internet se ele existir na página
            if (containerInternet2025) {
                containerInternet2025.style.display = (valorSelecionado === '2025_internet') ? 'block' : 'none';
                containerInternet2025.style.height = (valorSelecionado === '2025_internet') ? '100%' : '0';
                containerInternet2025.style.overflow = (valorSelecionado === '2025_internet') ? 'visible' : 'hidden';
            }

            // Força o Plotly a redimensionar o mapa ativo
            window.dispatchEvent(new Event('resize'));
        });
    }

    // =========================================================================
    // 3. LÓGICA DE ABRANGÊNCIA (DF vs NACIONAL)
    // =========================================================================
    const selectLocal = document.getElementById("local-select");
    const todosBlocosDf = document.getElementById("bloco-kpi-df");
    const todosBlocosNacional = document.getElementById("bloco-kpi-nacional");


    if (selectLocal) {
        selectLocal.addEventListener('change', function() {
            const abrangencia = this.value;
            const ehNacional = abrangencia === 'br';

            // Loop inteligente: Altera todos os blocos DF da página
            todosBlocosDf.forEach(bloco => {
                bloco.style.display = ehNacional ? 'none' : 'block';
            });

            // Loop inteligente: Altera todos os blocos Nacionais da página
            todosBlocosNacional.forEach(bloco => {
                bloco.style.display = ehNacional ? 'block' : 'none';
            });
            
            // Caso existam mapas dinâmicos acoplados a essa troca, força o redimensionamento
            window.dispatchEvent(new Event('resize'));
        });
    }
});