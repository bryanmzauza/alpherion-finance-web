# Fontes locais

Servidas via `next/font/local` (site.md §3.4: sem requisição ao Google Fonts).

| Arquivo | Família | Eixos | Subset | Licença |
| --- | --- | --- | --- | --- |
| `playfair-display-latin-wght-normal.woff2` | Playfair Display (H1–H2, números de destaque) | `wght` 400–900 | latin | OFL-1.1 (`LICENSE-playfair-display.txt`) |
| `inter-latin-wght-normal.woff2` | Inter (todo o resto) | `wght` 100–900 | latin | OFL-1.1 (`LICENSE-inter.txt`) |

Origem: pacotes `@fontsource-variable/inter` e `@fontsource-variable/playfair-display` 5.3.0 (copiados; não são dependência).

## `og/` — só para o gerador de Open Graph

`next/og` (Satori) não lê WOFF2, por isso `lib/og.tsx` usa estas cópias em WOFF. Não são servidas ao navegador.

| Arquivo | Família / peso | Origem | Licença |
| --- | --- | --- | --- |
| `og/playfair-display-600.woff` | Playfair Display 600 | Google Fonts (`fonts.gstatic.com`, v40) | OFL-1.1 |
| `og/inter-400.woff` | Inter 400 | Google Fonts (`fonts.gstatic.com`, v20) | OFL-1.1 |
