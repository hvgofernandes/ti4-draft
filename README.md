# TI4 Draft

Frontend do Twilight Draft Pick em React, TypeScript e Vite. As regras de negócio permanecem nas RPCs do Supabase; a camada de aplicação acessa-as por contratos que podem receber uma implementação de API própria no futuro.

## Desenvolvimento local

1. Inicie o Supabase local com `supabase start`.
2. Copie `.env.example` para `.env.local` e preencha `VITE_SUPABASE_PUBLISHABLE_KEY` com a chave publishable exibida por `supabase status`.
3. Instale dependências com `npm install`.
4. Inicie o frontend com `npm run dev`.

O URL e a chave são lidos exclusivamente das variáveis `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY`. Não coloque chaves secretas do Supabase no frontend.

### Limpeza dos dados locais

O utilitário administrativo abaixo audita os drafts locais sem alterar dados:

```powershell
npm run dev:reset-local-data
```

Para remover drafts, participantes, picks e dependências transitórias, use explicitamente:

```powershell
npm run dev:reset-local-data -- --execute
```

O script obtém o endpoint pelo `supabase status` e se recusa a executar quando o hostname não é `localhost`, `127.0.0.1` ou `::1`. Perfis persistentes, catálogo, schema e migrations são preservados. Não use esse comando para dados que devam ser mantidos.

### Estado do deploy remoto

**REMOTE DEPLOY PENDING:** o projeto remoto permanece intencionalmente no histórico `20260929172259`. As migrations locais `20260929190000`, `20260930120000`, `20260930150000`, `20261003160000`, `20261003160100` e `20261003160200` devem ser aplicadas de verdade e em ordem durante uma futura fase explícita de deploy. Não marque essas migrations como aplicadas sem executar seu SQL.

## Verificação

- `npm run check`: verificação TypeScript.
- `npm run build`: verificação TypeScript e build de produção.
- `npm run preview`: serve o build local.

`app.js` e `style.css` na raiz permanecem como referência do frontend anterior; a nova aplicação começa em `src/main.tsx`.

## Fase 3.1: catálogo e conteúdo do draft

O catálogo global contém `content_sets` e `factions`. Cada sala guarda seus conjuntos em `draft_content_sets`; Base Game é selecionado ao criar a sala. O host pode trocar a seleção pela RPC `set_draft_content_sets(uuid, uuid[])` somente em `waiting`. A RPC incrementa `drafts.content_version`, e os clientes participantes recarregam a seleção quando recebem esse evento Realtime. As tabelas do catálogo são legíveis por usuários autenticados; os dados de cada sala são legíveis apenas por participantes.

`start_draft` valida que existe ao menos um conjunto habilitado e facções ativas suficientes para um pick por jogador. `make_pick(uuid, uuid)` recebe `faction_id` e valida turno, disponibilidade e unicidade no banco. A coluna textual `picks.faction` permanece para leitura de escolhas locais antigas; novas escolhas são vinculadas ao catálogo.

Para aplicar e verificar **somente no Supabase local**:

```powershell
supabase migration up --local
npm run check
npm run build
supabase db lint --local --schema public
node supabase/tests/draft_rpc_regression.mjs
Get-Content supabase/tests/phase_3_1_database_regression.sql -Raw | docker exec -i supabase_db_ti4-draft psql -U postgres -d postgres -v ON_ERROR_STOP=1
git diff --check
```

O teste SQL requer três usuários anônimos locais, criados pelo teste JavaScript, e usa `ROLLBACK`. O painel visual com catálogo, fontes, progresso e resultados está em [docs/phase-3.1-progress.html](docs/phase-3.1-progress.html); abra o arquivo diretamente no navegador.

## Fase 3.1.6: preparação dos símbolos

A [galeria de QA](docs/faction-assets-qa/index.html) e o [manifesto](docs/faction-assets-qa/faction-assets-manifest.json) registram os 64 slugs do catálogo. O pipeline reproduzível fica em [scripts/faction-assets](scripts/faction-assets); seus parâmetros e bloqueios estão no [README da galeria](docs/faction-assets-qa/README.md). Abra a galeria pelo Vite em `http://127.0.0.1:5173/docs/faction-assets-qa/`.

Os símbolos oficiais são extraídos do atlas preservado; os sources Discordant Stars foram localizados no acervo local. A galeria compara fonte, isolamento e normalização, com hashes, parâmetros, métricas e alertas. Os PNGs são candidatos aguardando revisão visual humana. Esta etapa não altera banco ou interface principal.
