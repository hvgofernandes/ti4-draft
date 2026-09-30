# Revisão independente — Fase 3.1.5

Revisor: subagente independente do implementador. Revisão de código e verificações locais somente leitura; nenhuma operação sobre os originais além de leitura.

## Resultado final

A abordagem é adequada para uma investigação conservadora. O scanner não executa Lua, não baixa URLs, mantém a proveniência por caminho do objeto e copia arquivos completos com verificação SHA256. A identidade das 30 facções vem da migração do catálogo TI4-Draft, com distribuição 17 base / 7 PoK / 6 Thunder’s Edge (incluindo Keleres conforme esse catálogo). Não há integração React/banco.

Verificações independentes executadas:

- Travessia iterativa própria do JSON: **4.623 objetos** com GUID e Name, todos sob ObjectStates; 304 objetos de topo. Há **4 objetos em States**. Uma segunda travessia restrita a ContainedObjects confirma exatamente os **4.617** do briefing. A diferença é explicada integralmente por **4 States + 2 ChildObjects** (Love Ball e um modelo sem nome). A travessia completa é mais abrangente e correta.
- GUIDs repetidos realmente existem. Usar caminho completo junto ao GUID evita tratar instâncias distintas como uma única instância.
- Inventário: **9.517 ocorrências, 1.390 URLs únicas, 1.177 URLs únicas com cache correlacionado**. Todos os vínculos retornados obedecem exatamente à remoção de caracteres não alfanuméricos ASCII do URL; **nenhuma colisão** entre URLs distintas após essa normalização no conjunto observado.
- As **121 associações finais, correspondentes a 92 arquivos de saída e 91 fontes únicas,** foram comparadas byte a byte com os originais; todos os hashes SHA256 registrados também conferiram.
- Nova comparação independente dos 2.861 registros de tamanho/mtime do cache com o snapshot inicial: **zero diferenças**.
- Aliases derivados do texto Lua cobrem as 30 facções; Naaz-Rokha usa NRA, Vuil’Raith usa Cabal, Last Bastion usa Bastion, Crimson Rebellion usa Rebellion. Firmament e Obsidian permanecem na mesma entrada; Keleres não aumenta a contagem de facções.

## Achados e limites

1. **Melhoria de cobertura incorporada:** a versão final seleciona FaceURL de cartas de referência e mostra a célula pelo CardID (resto da divisão por 100), NumWidth e NumHeight. Os 30 vínculos usam um atlas compartilhado, copiado integralmente uma vez. Firmament/Obsidian tem token conjunto; Keleres mostra a referência Mentak. As variantes Keleres em States sem CustomDeck próprio não geram novas prévias e precisam ser consideradas na validação humana.
2. A classificação ambiguous decorre de haver mais de um candidato, não de uma probabilidade calculada de identidade. Isso é conservador e deve ser explicitado. Não há símbolo isolado automaticamente aprovado; todas as 30 facções continuam dependentes de validação humana.
3. A correlação é exata e adequada ao cache observado, mas não pretende recuperar arquivos remotos ausentes, nomes alternativos, diferenças de caixa nem converter rawt. Nenhum desses arquivos deve ser apresentado como candidato confirmado.
4. O teste de integridade global é tamanho/mtime; somente JSON, catálogo e fontes copiadas recebem SHA256. Isso está corretamente declarado no relatório, sem alegar auditoria byte a byte de todo o cache.
5. A proteção de destino cobre a raiz Mods e a raiz do projeto inferida a partir da migração. O uso atual é seguro. Para reutilização genérica, convém validar separadamente que source não esteja dentro de output, e testar explicitamente a raiz do projeto: cat.parent.parent.parent depende da localização convencionada da migração.
6. O implementador acrescentou hash de URL aos nomes individuais e hash de conteúdo ao atlas compartilhado; isso reduz colisões em reexecuções. A cópia segura recusa sobrescrever conteúdo divergente.

Nenhum achado indica alteração dos originais ou contaminação do projeto principal. Esta revisão não constitui aprovação visual dos assets e não libera a Fase 3.2.

## Testes finais

Executados os 7 testes automatizados da versão final: todos passaram, cobrindo recursão, exclusão de descendentes na associação local, extração de URLs, correlação exata, proteção de cópias e caminhos com espaços, catálogo, JSON e estrutura/links HTML. Nova comparação independente byte a byte confirmou todas as 121 associações finais. A galeria contém 30 seções e 121 imagens; os destinos existem. **Layout e interação em navegador não foram verificados:** a política de navegação bloqueou file://, conforme informado pelo implementador. A inspeção HTML e dos cálculos CSS não substitui revisão visual no navegador.

Adendo de consolidação: após esta revisão, a suíte foi ampliada para 9 testes e passou integralmente (ver tests-result.txt), incluindo execução com cache ausente/correspondência parcial rejeitada e validação dos 30 índices do atlas. O relatório final registra 92 arquivos copiados e zero colisões de normalização.

## Adendo da correção de entrega
A limitação histórica de navegação acima foi resolvida na entrega realocada: a galeria foi aberta via HTTP no Vite, com CSS, imagens, filtros, busca e detalhes testados. Consulte delivery-test.md e delivery-verification.json. A investigação não foi refeita.
