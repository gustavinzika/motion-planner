---
name: motion-planner
description: Analisa uma imagem (pixel art, ilustração, foto, cena de jogo) e produz um PLANO de animação — inventário dos elementos, o que pode se mover e como, hierarquia de movimento, pontos de fixação — num manifest JSON com overlay visual para revisão. Use sempre que o usuário quiser dar vida, animar, aplicar motion, parallax, loop ou rig a uma imagem estática, ou pedir para detalhar/mapear/segmentar os elementos de uma imagem antes de animar (água, personagens, cabelo, capa, bandeira, lanternas, céu, objetos), mesmo que não diga "manifest". Também em inglês, como image animation plan, motion planning, layer breakdown. NÃO gera máscaras, assets recortados nem animação rodando.
---

# Motion Planner

Transforma uma imagem estática em um **plano de animação inspecionável**: o que existe, onde (com a incerteza declarada), como poderia se mover e o que ainda falta para animar de verdade.

## Por que esta skill existe

Um modelo de visão é bom em **semântica** (o que é, o que faz sentido mover, como) e fraco em **geometria** (coordenadas exatas, contornos). Quando se pede a ele "descreva tudo para animar", ele mistura as duas coisas e entrega coordenadas com cara de medida, que são palpites. A animação então "vai no ponto errado".

A skill separa os dois papéis: você decide **o quê e como**, e **marca como estimativa** tudo que é posição. O resultado é um plano honesto, em que cada campo crítico diz se foi medido, estimado ou inferido.

## O que entrega (escopo `planning_only`)

1. `manifest.json` seguindo `schema/manifest.schema.json`
2. `overlay.png` (+ `overlay.legend.md`) gerado **a partir do manifest**, com caixas numeradas, pivôs e fixações
3. Um resumo curto: o que foi mapeado, o que está pendente, o que precisa de decisão humana

**Fora do escopo:** detecção/segmentação por modelos (Grounding DINO, SAM), profundidade, inpainting, exportar para Canvas/WebGL/Spine, preview animado. O plano lista esses requisitos em `limits.extraction_requirements` para uma etapa futura. Não ofereça o preview como se estivesse pronto: sem máscaras, ele arrasta o fundo junto e esconde erros de análise atrás de movimento.

## Fluxo

1. **Obter os fatos mensuráveis da imagem.** Largura, altura e sha256 vêm de um comando (`python3 -c "from PIL import Image..."`, `sha256sum`), com `dimensions_provenance: "measured"`. Se não houver ambiente para rodar, use `null` e diga que não mediu.
2. **Decidir o que importa animar.** Se o usuário disse quais elementos, mapeie esses. Se não disse, escolha os que têm movimento natural e liste o resto como estático (ele segue o pai via `transform_parent`). Não mapeie cada detalhe: elementos demais poluem o overlay e escondem o que importa.
3. **Montar o manifest.** Leia "Regras do manifest" abaixo. Use `examples/caravela.manifest.json` como referência de formato, sem copiar regras de navio ou de pixel art para imagens que não são isso.
4. **Validar:** `python3 scripts/validate_manifest.py manifest.json`. Erros bloqueiam; avisos entram no resumo final. JSON válido prova estrutura, não qualidade visual.
5. **Gerar o overlay:** `python3 scripts/render_overlay.py manifest.json imagem.png out/overlay.png`. Depois **olhe o resultado** (`view`) e corrija o que estiver visivelmente errado. Para áreas pequenas ou densas, use `--crop <id> --scale 3`. Essa conferência continua sendo estimativa visual: não promove nada a `verified`.
6. **Entregar** com o resumo (ver "Resumo final") e pedir decisão humana só nos pontos em que ela muda o resultado.

## Regras do manifest

**Cada campo crítico carrega `status` e `provenance`.** São `bbox`, `transform_parent`, `draw_order`, `region_bbox`, `pivot`, `attachment` e `motion`.

- `provenance`: `measured` (ferramenta mediu), `vlm_estimate` (você leu a imagem), `inferred` (deduzido), `design_choice` (decisão de animação), `human` (pessoa confirmou).
- `status`: `proposed`, `needs_review`, `verified`, `unknown`.
- `verified` só existe com `provenance` `measured` ou `human` **e** `evidence` preenchido. Você conferir o overlay não é isso. Se ninguém revisou, `limits.human_review_performed` é `false`.
- Se não dá para determinar, use `value: null` e `status: unknown`. Inventar uma coordenada para preencher o campo é pior que deixar vazio, porque o consumidor confia nela.
- Nunca use `confidence` numérico. Um 0.91 sem método de cálculo é ruído com aparência de dado.

**Três relações diferentes, que não se misturam:**

| Campo | Pergunta que responde | Exemplo |
|---|---|---|
| `transform_parent` | Quem me carrega quando se move? | O personagem herda o balanço do navio |
| `draw_order` | Quem fica na frente de quem? | O corrimão cobre as pernas do timoneiro |
| `coupling` (nas regiões) | Meu movimento se relaciona ao de outra região? | Espuma da proa acompanha o balanço |

Misturar `transform_parent` com `draw_order` é o erro mais comum: pai não é o que está "atrás". Se uma entidade contém partes que ficam na frente e atrás de outras (ex.: casco com corrimão), registre isso em `order_note` e peça `layer_split`.

**Entidade ≠ região de movimento.** A entidade diz o que existe; a região diz que parte dela se move e como. Um personagem tem uma entidade e várias regiões (cabelo, capa).

**Movimento herdado não se duplica.** Se o navio sobe e desce (`bob`), os filhos herdam via `transform_parent`. Dar `bob` próprio a um filho soma os dois movimentos. O validador avisa.

**Máscara:** `mask: null` quando não existe. Nunca aponte um caminho fictício. Uma bbox retangular não é máscara e uma bbox confirmada também não prova contorno.

**Pivô e fixação:** declare o `space` (`image` ou `bbox_local`) em todo ponto. A fixação diz onde a parte está presa (ponta da bandeira no mastro, raiz do cabelo na cabeça); é o que impede o "ponto incorreto".

**Partes ocultas:** quando um movimento revelaria o que está atrás (capa se afastando do corpo), liste `hidden_content` em `requires`. Não invente o conteúdo escondido; se um dia for reconstruído, marque como `inferred`.

**Presets de movimento** estão em `references/motion_presets.md`. São pontos de partida configuráveis, não verdades por categoria. Antes de aceitar um preset, cheque contatos (o que toca o quê), cordas tensionadas e luz/reflexo.

**Atributos descritivos** (cores, roupa, aparência) vão em `attributes`, como texto livre, e não afetam movimento. Gênero só se o usuário pedir, e então como aparência de apresentação, nunca como fato sobre a pessoa.

## Quando perguntar ao usuário

Entregue resultados concretos primeiro (manifest + overlay) e depois pergunte, de forma pontual, só quando a ambiguidade muda uma destas coisas: **identidade** (o que é aquilo?), **âncora** (onde está preso?), **contorno** (o que entra na máscara?), **parte oculta** (o que há atrás?). Não imponha aprovação humana global se as verificações objetivas bastarem. "Final" não é sinônimo de "aprovado".

## Resumo final (curto)

- Quantos elementos e regiões foram mapeados e quantos campos estão `needs_review`
- Avisos do validador e o que cada um significa
- Pendências em `requires` (máscaras, emissão, hidden_content) — ou seja, o que falta para animar de verdade
- Perguntas pontuais ao usuário, se houver
- Uma frase dizendo que as coordenadas são estimativas e que o manifest **não está pronto para renderizar**

## Arquivos

- `schema/manifest.schema.json` — o contrato
- `scripts/validate_manifest.py` — referências, ciclos, limites, regra de `verified`, movimento duplicado, oclusão incoerente (usa `jsonschema` se instalado)
- `scripts/render_overlay.py` — overlay determinístico (requer Pillow); ampliação sem suavizar pixels
- `references/motion_presets.md` — catálogo de movimentos e armadilhas
- `references/evaluation.md` — como testar esta skill e critérios de aceitação propostos
- `examples/caravela.manifest.json` — exemplo completo (cena de pixel art com 27 entidades e 23 regiões)
