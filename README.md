# TI4 Draft

Frontend do Twilight Draft Pick em React, TypeScript e Vite. As regras de negócio permanecem nas RPCs do Supabase; a camada de aplicação acessa-as por contratos que podem receber uma implementação de API própria no futuro.

## Desenvolvimento local

1. Inicie o Supabase local com `supabase start`.
2. Copie `.env.example` para `.env.local` e preencha `VITE_SUPABASE_PUBLISHABLE_KEY` com a chave publishable exibida por `supabase status`.
3. Instale dependências com `npm install`.
4. Inicie o frontend com `npm run dev`.

O URL e a chave são lidos exclusivamente das variáveis `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY`. Não coloque chaves secretas do Supabase no frontend.

## Verificação

- `npm run check`: verificação TypeScript.
- `npm run build`: verificação TypeScript e build de produção.
- `npm run preview`: serve o build local.

`app.js` e `style.css` na raiz permanecem como referência do frontend anterior; a nova aplicação começa em `src/main.tsx`.
