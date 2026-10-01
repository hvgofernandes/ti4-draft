# Cinco extrações especiais de Discordant Stars

As cinco imagens nesta pasta são prévias para revisão visual, não aprovações de produção. Os originais e as cópias em `assets/factions/source/discordant-stars/` permanecem intactos. O script `scripts/faction-assets/discordant_special_masks.py` gera as prévias com GrabCut clássico (8 iterações), retém componentes de pelo menos 100 pixels, suaviza apenas 1 pixel de alpha e mantém os pixels RGB dos sources sem redimensionamento. Os recortes, retângulos, caminhos, dimensões e SHA-256 individuais estão em `manifest.json`.

Foram inspecionadas as cinco prévias nos fundos claro e escuro. Florzen, Vaden, Zelian e Nokar tiveram resíduos de fundo externos removidos; Vaylerian recuperou as três pontas e a base, mas mantém glow suave presente no original (`SOURCE_GLOW_REVIEW`). A inspeção humana final continua necessária.

Validação local: cinco PNGs RGBA, alpha de 0 a 255, margens transparentes de 16 pixels, hashes das cópias iguais aos originais e nenhum arquivo de origem alterado. Uma segunda execução gerou exatamente os mesmos cinco hashes. O SHA-256 da concatenação dos cinco hashes de prévia, na ordem do `manifest.json` e separados por `|`, foi `2e1f086fde8da18ee0ca21f5295916454a6385878c90d26eea5a2423c9d3b20b` nas duas execuções.

Os PNGs nesta pasta não substituem os intermediários em `assets/factions/intermediate/discordant-stars/` até que o extrator principal integre as máscaras e sua revisão seja repetida.
