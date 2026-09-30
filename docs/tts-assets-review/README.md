# Entrega local corrigida

Diretório: `C:\Projetos\ti4-draft\docs\tts-assets-review`

Abra **http://127.0.0.1:5173/docs/tts-assets-review/** com o Vite do projeto em execução (`npm run dev -- --host 127.0.0.1 --port 5173`). O servidor de desenvolvimento serve docs diretamente; não há cópia em public, alteração da configuração Vite nem inclusão na interface de produção. Em outro computador, use a porta informada pelo Vite.

Entrada local: `index.html`. Todas as imagens, estilos e filtros estão contidos nesta pasta. O atlas é compartilhado; nenhum asset foi duplicado para servir a página. Caminhos Mods/ no relatório são identificadores de proveniência histórica, não dependências do cache.

A investigação não foi refeita. Os scripts e resultados da investigação original são preservados; a verificação de entrega está em `delivery-verification.json` e `delivery-test.md`.

---

# TI4-Draft — Fase 3.1.5: revisão de candidatos TTS

Abra **index.html** no navegador local. Mantenha a pasta `candidates` junto ao HTML. Não exige internet nem servidor. As 30 facções estão organizadas na ordem do catálogo (17 Base, 7 PoK, 6 Thunder’s Edge/oficial associado), com filtros de conjunto, status e busca.

## Resultado

- 30 facções procuradas; 0 fortes, 30 ambíguas, 0 fracas isoladas, 0 sem resultado.
- 121 associações de candidatos: 4 por facção, exceto Ghosts of Creuss com 5.
- 91 arquivos-fonte distintos. O atlas comum das 30 fichas é copiado apenas uma vez. Outras cópias mantêm nomes por facção, portanto existem 92 arquivos na pasta candidates.
- Nenhum símbolo isolado foi certificado como pronto para uso. Texturas de fichas (confiança média), retratos, tiles e atlas de referência (confiança baixa como asset final) contêm emblemas misturados com outros elementos.
- A confiança descreve a adequação como símbolo; a associação nominal à facção é sustentada pelo JSON. “Ambígua” significa múltiplas opções ainda não aprovadas, não uma atribuição incerta do nome da facção.
- Todos os candidatos requerem validação humana. Nenhum foi aprovado automaticamente.

## JSON e recursão

Fonte: `Mods (origem histórica)\Workshop\1288687076.json`.

`SaveName = Twilight Imperium IV`; 304 ObjectStates. A recursão genérica percorre todos os dicionários/listas, incluindo ObjectStates, ContainedObjects, States, ChildObjects, CustomUIAssets e AttachedDecals.

Contagem: **4.623 objetos = 4.617 pela recursão ContainedObjects + 4 States + 2 ChildObjects**. GUIDs repetidos são preservados, diferenciados pelo caminho. A pesquisa de URLs também inspeciona campos de texto, LuaScript e LuaScriptState; Lua nunca é executado. Textos globais não atribuem indiscriminadamente todas as URLs a todas as facções.

Autoridade: `C:\Projetos\ti4-draft\supabase\migrations\20260930150000_content_catalog_and_draft_configuration.sql`. Nomes, slugs e conjuntos vêm desta migration. Aliases vêm de pares `id/tokenName` do Lua do próprio mod; normalização remove pontuação/artigo. As exceções verificadas Firmament/Obsidian e Keleres aparecem no relatório. Discordant Stars não foi minerado nem copiado; a varredura estrutural geral naturalmente pode inventariar URLs presentes no JSON inteiro.

## Correlação URL → cache

Método validado empiricamente: remover da URL todos os caracteres que não sejam ASCII `A–Z`, `a–z`, `0–9`; comparar **exatamente** com o nome do arquivo sem extensão, preservando maiúsculas/minúsculas. A extensão vem do arquivo existente. Nenhuma busca por prefixo ou por trecho substitui essa correlação.

Foram inventariadas 9.517 ocorrências e 1.390 URLs distintas; 1.177 URLs distintas têm correspondência local nas pastas indexadas. As demais 213 incluem referências não visuais/de execução: não representam 213 emblemas ausentes. `Images Raw` foi indexado, mas `.rawt` não foi tratado como imagem de navegador. As imagens selecionadas em `Images` foram verificadas com Pillow antes da cópia. Sem downloads.

## Candidatos e ambiguidades

As imagens `Button`/decals são painéis ilustrados, não ícones puros. Texturas `Command Token`/`Owner Token` são atlas com várias faces. A ficha de referência usa `CardID % 100` e `NumWidth/NumHeight` para mostrar a célula correta de um atlas 7090×4962, grade 5×6. O HTML também oferece zoom aproximado do canto com o emblema, apenas por CSS: o arquivo copiado continua integral e inalterado.

Atenção especial a Ghosts of Creuss (duas texturas de fichas), Council Keleres (nomes/variantes Mentak, Xxcha e Argent no mod) e Firmament/Obsidian (identidade conjunta do catálogo e emblema combinado na referência). A galeria não certifica que uma versão visual específica deva ser usada.

## Tabela das 30 facções

| Faction | Content Set | Candidates | Confidence | Status |
|---|---|---:|---|---|
| The Arborec | base | 4 | medium / low | ambígua — validação humana |
| The Barony of Letnev | base | 4 | medium / low | ambígua — validação humana |
| The Clan of Saar | base | 4 | medium / low | ambígua — validação humana |
| The Embers of Muaat | base | 4 | medium / low | ambígua — validação humana |
| The Emirates of Hacan | base | 4 | medium / low | ambígua — validação humana |
| The Federation of Sol | base | 4 | medium / low | ambígua — validação humana |
| The Ghosts of Creuss | base | 5 | medium / low | ambígua — validação humana |
| The L1Z1X Mindnet | base | 4 | medium / low | ambígua — validação humana |
| The Mentak Coalition | base | 4 | medium / low | ambígua — validação humana |
| The Naalu Collective | base | 4 | medium / low | ambígua — validação humana |
| The Nekro Virus | base | 4 | medium / low | ambígua — validação humana |
| Sardakk N'orr | base | 4 | medium / low | ambígua — validação humana |
| The Universities of Jol-Nar | base | 4 | medium / low | ambígua — validação humana |
| The Winnu | base | 4 | medium / low | ambígua — validação humana |
| The Xxcha Kingdom | base | 4 | medium / low | ambígua — validação humana |
| The Yin Brotherhood | base | 4 | medium / low | ambígua — validação humana |
| The Yssaril Tribes | base | 4 | medium / low | ambígua — validação humana |
| The Argent Flight | pok | 4 | medium / low | ambígua — validação humana |
| The Empyrean | pok | 4 | medium / low | ambígua — validação humana |
| The Mahact Gene-Sorcerers | pok | 4 | medium / low | ambígua — validação humana |
| The Naaz-Rokha Alliance | pok | 4 | medium / low | ambígua — validação humana |
| The Nomad | pok | 4 | medium / low | ambígua — validação humana |
| The Titans of Ul | pok | 4 | medium / low | ambígua — validação humana |
| The Vuil'Raith Cabal | pok | 4 | medium / low | ambígua — validação humana |
| Last Bastion | thunders-edge | 4 | medium / low | ambígua — validação humana |
| The Deepwrought Scholarate | thunders-edge | 4 | medium / low | ambígua — validação humana |
| The Crimson Rebellion | thunders-edge | 4 | medium / low | ambígua — validação humana |
| The Ral Nel Consortium | thunders-edge | 4 | medium / low | ambígua — validação humana |
| The Firmament / The Obsidian | thunders-edge | 4 | medium / low | ambígua — validação humana |
| The Council Keleres | thunders-edge | 4 | medium / low | ambígua — validação humana |

## Arquivos entregues

- `scripts/scan_tts.py`: scanner reutilizável, Python 3 + Pillow.
- `scripts/test_scan_tts.py`: testes automatizados.
- `tests-result.txt`: resultado da suíte.
- `tts-faction-assets-report.json`: relatório principal, proveniência, hashes, dimensões, aliases, candidatos, limitações e integridade.
- `url-cache-inventory.json`: todas as ocorrências de URLs, caminhos e correspondências locais.
- `source-metadata-before.json`: inventário de segurança anterior à execução final.
- `index.html`: galeria local.
- `candidates/`: cópias integrais, nomes legíveis; os caminhos absolutos estão no JSON.
- `factions-summary.csv`: tabela importável.
- `independent-review.md`: revisão independente.

## Scripts históricos da investigação

Comandos históricos da investigação (não necessários para abrir ou testar a entrega):

```powershell
& 'C:\Users\Hugo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\scripts\scan_tts.py
& 'C:\Users\Hugo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .\scripts\test_scan_tts.py
```

O scanner também aceita `--source`, `--mods`, `--catalog`, `--output`. Caminhos com espaços foram exercitados na execução real e em testes. Ele recusa output dentro da árvore TTS/projeto principal, cópia sobre a fonte, escape da pasta de destino e sobrescrita de candidato diferente.

## Segurança, revisão e limites

Nenhum original do TTS foi modificado, movido, renomeado ou apagado. O scanner só lê originais e copia para outputs. Nenhuma alteração ao React, banco, migrations, RPCs ou Fase 3.2.

Verificação: tamanho e mtime de 2.861 arquivos da árvore Mods antes/depois, sem diferenças; SHA-256 do JSON, catálogo e de todas as fontes copiadas, sem diferenças. Cópias conferidas por SHA-256. Não é uma auditoria byte a byte de arquivos não utilizados do cache.

O revisor independente conferiu recursão, aliases, URLs/cache, hashes, atlas e falsos positivos. Foram incluídas as fichas de referência para não ignorar uma alternativa melhor aos retratos. Os detalhes e limitações constam da revisão.

A estrutura HTML, seus 30 blocos, referências locais e arquivos foram testados. Na investigação original, a renderização e interação dos filtros no navegador não haviam sido verificadas: a ferramenta de navegação bloqueou o protocolo file:// por política; não houve tentativa de contornar esse bloqueio. Imagens-fonte representativas e o atlas completo foram inspecionados visualmente.

Próximo passo: validar visualmente as 30 facções na galeria e escolher a fonte/variante de cada emblema. Recorte, tratamento de fundo e integração permanecem pendentes de decisão; esta entrega termina na investigação da Fase 3.1.5.

Validação automatizada final: **9 testes passaram**, incluindo cache ausente, rejeição de prefixo falso e correspondência dos 30 índices do atlas.

## Verificação da correção de entrega
A galeria foi efetivamente aberta pelo Vite. Todos os 92 arquivos de imagem passaram na checagem HTTP e SHA-256; filtros e busca foram testados no navegador. Veja delivery-test.md, delivery-verification.json e delivery-preview.png. A suíte local resultou em 8 testes aprovados e 1 comparação histórica com o TTS ignorada intencionalmente, sem acesso ao cache.
