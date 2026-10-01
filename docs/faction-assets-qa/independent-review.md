# Revisão independente — Fase 3.1.6

Estado: **64 candidatos técnicos inspecionados; nenhum aprovado visualmente em nome do usuário.** `READY_FOR_REVIEW` indica que o candidato pode ser examinado pelo Product Owner, não aprovação definitiva.

## Método e integridade

- Conferi os 64 slugs do catálogo (17 Base, 7 PoK, 6 Thunder's Edge e 34 Discordant Stars), as 30 fontes oficiais contra os candidatos TTS anteriores e as 34 fontes Discordant Stars contra o acervo local.
- Comparei os 34 emblemas DS com o recorte original dos reference cards e, nos casos ambíguos, com as folhas `7 Tokens`. Inspecionei intermediários e finais sobre fundos claro e escuro; usei composições coloridas para distinguir regiões transparentes de pixels escuros.
- Recalculei os hashes das 34 fontes DS originais, das cópias preservadas e dos intermediários: todos coincidem com `discordant-stars-mapping.json`. Em **4.914.244 pixels com alpha > 0**, o RGB dos intermediários coincide exatamente com o pixel correspondente da fonte em `intermediateOffset`; zero divergências. A menor margem alpha dos intermediários DS é 16 px.
- Recalculei os hashes dos 64 PNGs finais contra o manifest: **64/64 coincidem e são distintos**. Todos são RGBA 512 × 512, com transparência real; a menor margem visível no canvas final é 71 px. Nenhum símbolo aparece cortado no contact sheet final.

## Símbolos oficiais (30)

Os 30 finais oficiais preservam identidade, proporção e componentes legítimos na revisão em grade. Seis máscaras intermediárias iniciais tinham linhas externas (Muaat, Naalu, Nekro, Xxcha, Vuil'Raith e Ral Nel); elas foram removidas antes da normalização final. O atlas original oferece símbolos nativos pequenos, aproximadamente 99–171 px; os 30 registros conservam avisos `LOW_SOURCE_RESOLUTION` e `TINY_FRAGMENTS_REVIEW`. O zoom humano deve avaliar nitidez e bordas.

Ghosts of Creuss usa uma textura alternativa. O token anterior de Council Keleres mostrava a variante Mentak, enquanto o atlas selecionado fornece um símbolo próprio Keleres. Firmament/Obsidian corresponde a uma única identidade no catálogo. Componentes separados de Winnu, Argent Flight, Mahact e Titans of Ul foram mantidos.

## Discordant Stars (34)

O acervo usado contém 33 faction reference cards e uma alliance reference card para Zelian. As 34 cópias de source preservam os originais. O processo não depende de cinco folhas `7 Tokens` cujo chunk auxiliar `iCCP` tem CRC inválido.

A comparação source/token revelou perdas reais nas primeiras máscaras. Foram corrigidos: lua de Axis, áreas internas de Celdauri e ponta de Olradin; discos cinza de Mortheus; folha roxa de Augurs; haste e asa verde de Tnelis; disco azul de Veldyr; painéis escuros de Ghoti, Ltokk e Nokar; e fundos indevidos dentro dos anéis de Kyro. As cinco máscaras especiais Florzen, Vaylerian, Vaden, Zelian e Nokar foram revisadas em fundos claro e escuro após integração. No contact sheet final, os 34 candidatos mantêm a identidade visual e não exibem novos blocos de fundo nem fragmentos externos evidentes.

As folhas de tokens ajudaram a distinguir espaços vazios de preenchimento perdido: o centro de Nivyn e os vãos de Vaden, Zealots, Lanefir e Rohdhnna acompanham o fundo da ficha, portanto a transparência é correta. Em Ghoti, Ltokk, Nokar e Veldyr, as áreas escuras pertencem ao emblema e foram preservadas. A textura retangular de Cheiran também pertence ao emblema.

**32 DS estão `READY_FOR_REVIEW`; dois permanecem `NEEDS_MANUAL_REVIEW`:**

- **Nivyn Star Kings:** foreground chega perto do limite inferior do recorte de referência. Não vi corte no final, mas a margem na fonte requer exame ampliado.
- **Vaylerian Scourge:** halo verde suave proveniente da fonte permanece ao redor das pontas e da base. Ele é visível no fundo escuro; decidir se a aparência é aceitável exige revisão visual.

## Conclusão

O conjunto de 64 tem rastreabilidade, alpha e dimensões consistentes e está pronto para revisão visual humana. Os 62 `READY_FOR_REVIEW` não equivalem a `FINAL_APPROVED`. Nivyn e Vaylerian exigem decisão visual específica antes de qualquer aprovação do conjunto.
