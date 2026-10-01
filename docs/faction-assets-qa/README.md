# Fase 3.1.6 — extração e QA dos 64 emblemas

A galeria mostra original (ROI, com ampliação da fonte completa), intermediate isolado e final normalizado. Os resultados são candidatos, nunca aprovação definitiva. Abra pelo Vite em http://127.0.0.1:5173/docs/faction-assets-qa/.

## Entrega desta rodada

64 vínculos de source, 64 intermediários e 64 finais: 30 oficiais do atlas e 34 DS (33 fichas de referência e a carta de aliança Zelian). Há 62 READY_FOR_REVIEW e 2 NEEDS_MANUAL_REVIEW: Nivyn pela proximidade do foreground ao crop e Vaylerian pelo glow difuso existente no source. Quarenta facções têm ao menos um alerta automático. Nenhum emblema DS já estava isolado com transparência: todos os 34 exigiram cleanup, mesmo nas fichas com alpha externo.

A ocupação alpha final varia de 8,7% a 50,3%, mediana 19,3%. Os sete outliers de peso são Argent, Free Systems, Li-Zho, Nivyn, Veldyr, Cheiran e Kolume; círculos/selos opacos e desenhos finos têm densidades legitimamente diferentes. Os 30 oficiais também são limitados pela ampliação máxima 2×, com sete fontes particularmente pequenas. O baseline foi mantido: uniformizar a área por aumento global não resolve a resolução dos oficiais. Uma futura calibração óptica por densidade deverá ser avaliada visualmente e respeitar o limite de escala; não foi aplicada nesta rodada.

Nove testes Python, validação completa, 261 caminhos HTTP, npm check/build e git diff --check passaram. Os hashes de 540 arquivos permaneceram iguais. Consulte qa-report.json, http-report.json, source-immutability-report.json, visual-consistency.json e independent-review.md para os detalhes.

## Fontes e rastreabilidade

O catálogo SQL permanece a autoridade: 17 Base, 7 PoK, 6 Thunder's Edge e 34 Discordant Stars. `official-mapping.json` preserva os 121 vínculos anteriores e os hashes dos 92 candidatos TTS. `official-extraction.json` registra as regiões e máscaras dos 30 emblemas oficiais do atlas. A comparação com fichas maiores não mostrou ganho seguro para os símbolos pequenos: textura e fundo prejudicam a extração. O atlas PNG foi mantido, com aviso de resolução quando necessário.

`discordant-stars-mapping.json` identifica cada nome/slug, arquivo original no acervo local, cópia preservada, hashes, crop, método e alertas. O acervo em `imports/discordant-stars/` é somente leitura e permanece ignorado pelo Git. Somente arquivos escolhidos para os símbolos são copiados; não se copia o acervo inteiro.

Os sources são imutáveis. Intermediates e finals são derivados regeneráveis. A segmentação usa processamento clássico e mantém as cores dos pixels da fonte; não há geração, redesenho ou reconstrução artística. Consulte o método/parametrização de cada registro para reproduzir a máscara.

## Execução

Requer Python, Pillow, NumPy e OpenCV headless; versões em `scripts/faction-assets/requirements.txt`. A instalação local de dependências em `.asset-pipeline-deps/` é ignorada pelo Git.

```powershell
python -m pip install --target .asset-pipeline-deps --no-deps -r scripts/faction-assets/requirements.txt
python scripts/faction-assets/extract_official.py
python scripts/faction-assets/extract_discordant.py
python scripts/faction-assets/build_assets.py
python scripts/faction-assets/generate_gallery.py
python scripts/faction-assets/validate_assets.py --require-complete
python scripts/faction-assets/summarize_qa.py
python scripts/faction-assets/test_pipeline.py
python scripts/faction-assets/test_http.py
python scripts/faction-assets/check_immutability.py check
```

Confira `--help` nos extratores antes de usar opções de amostra. Os scripts recusam sobrescrever fontes com conteúdo diferente. O builder valida hashes antes de normalizar.

`source-immutability-baseline.json` registra o acervo DS inteiro, todas as fontes preservadas e todos os candidatos TTS anteriores antes da execução final. O check compara arquivos, tamanhos e SHA-256; não sobrescreve esse baseline. Há 34 fichas DS selecionadas, totalizando 680.393.969 bytes. O atlas é compartilhado pelos 30 oficiais; as 30 fichas anteriores continuam preservadas. Assim, 64 vínculos de source no manifest não significam 64 arquivos originais distintos.

## Normalização e limites

Baseline preservado: PNG RGBA 512×512, maior lado até 72%, ampliação máxima 2×, proporção preservada, centralização e LANCZOS. Símbolos pequenos podem ocupar menos de 72% porque ampliar mais não cria detalhe. As métricas incluem bbox, aspecto, área alpha ponderada, ocupação, densidade, componentes, fragments e fringe. `visual-consistency.json` compara a população e sinaliza outliers; não ajusta a arte automaticamente.

O QA verifica 64 slugs/sources/intermediates/finals, hashes de originais e cópias, alpha, margens, aspecto, área, duplicatas e arquivos excedentes. Um componente desconectado pode ser parte legítima do desenho; warnings pedem inspeção e não apagam componentes. Alpha binário nos oficiais exige atenção em zoom; LANCZOS suaviza o resultado sem inventar detalhe.

## Revisão humana

Use filtros de conjunto, status, warnings e origem; alterne checkerboard, claro e escuro. `READY_FOR_REVIEW` significa candidato para avaliação humana. `NEEDS_MANUAL_REVIEW` identifica uma limitação concreta registrada, não aprovação. Nenhum asset recebe `FINAL_APPROVED` nesta fase.

Revise especialmente Ghosts of Creuss, Council Keleres (o token anterior tinha variante Mentak; o atlas fornece símbolo próprio, variantes devem permanecer documentadas), Mentak e Firmament/Obsidian. As contact sheets são auxiliares; use as três imagens ampliadas de cada card para aprovação. Esta fase não integra imagens no React, não cria image_url e não modifica banco ou regras do draft.
