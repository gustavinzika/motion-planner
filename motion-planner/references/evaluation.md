# Como testar esta skill

**Status:** plano proposto numa discussão entre Claude e Codex. Nada aqui foi executado ainda. Os critérios são hipóteses de trabalho, não resultados validados, e não há limiar universal: tolerâncias dependem da escala e da função de cada elemento.

## Por que testar antes de expandir

Esta skill entrega um plano, não assets. A dúvida real é se esse plano é **útil na prática**: se as caixas e âncoras estimadas ajudam alguém a animar, ou se corrigi-las dá mais trabalho que descrever à mão. Só dá para saber testando em imagens diferentes.

## Conjunto de teste barato

Quatro imagens, escolhidas para estressar pontos diferentes:

1. A caravela (`examples/`), com tecido, água, luz e personagens
2. Uma foto com oclusão (pessoa atrás de objeto)
3. Uma ilustração simples (poucos elementos, bordas limpas)
4. Uma imagem com detalhes finos e baixo contraste

**Antes de rodar a skill**, escolha em cada imagem alguns elementos que realmente precisam de movimento e marque os pontos de fixação visíveis. Isso forma uma referência leve e evita julgar o resultado depois de vê-lo.

## O que registrar em cada imagem

- Elementos omitidos e elementos inventados
- Identidade correta (o que a skill chamou de "vela" é uma vela?)
- Encaixe da bbox (IoU ajuda, mas não mede máscara nem qualidade de âncora)
- Erro de âncora em pixels, e também normalizado pela dimensão do próprio elemento
- Ciclos e referências quebradas no manifest
- Contradições de contato ou de movimento
- Tempo gasto e número de correções humanas

O overlay deve ser gerado diretamente do JSON, nunca em duas versões manuais que possam divergir.

## Critérios de aceitação iniciais (propostos)

- JSON válido e referências consistentes (o validador passa sem erros)
- Todo elemento prioritário está contemplado ou marcado como não localizado
- Nenhuma coordenada inferida aparece rotulada como medida
- Nenhum movimento exige separar partes que o manifest não especifica
- Limites explícitos (`planning_only`, pendências, requisitos de extração)
- Um revisor identifica no overlay cada elemento crítico e corrige um erro local **sem refazer a análise inteira**
- Reuso: funciona em pelo menos uma imagem diferente da caravela, sem regra obrigatória de navio ou de pixel art

## Critério de corte

Se corrigir o plano exigir mais trabalho que descrever o mesmo à mão, simplifique o fluxo em vez de acrescentar camadas.

## Riscos esperados (hipóteses, sem teste ainda)

- Inventário detalhado, mas inútil para decidir movimento
- Caixas plausíveis, porém erradas
- Âncora inventada para objeto parcialmente oculto
- Hierarquia correta semanticamente e errada para o movimento
- Excesso de IDs no overlay (use `--only` e `--crop`)
- Presets que ignoram contatos, cordas tensionadas ou luz/reflexo
- Schema genérico demais para qualquer consumidor interpretar

O overlay melhora a inspeção; não prova exatidão. O validador prova estrutura; não prova qualidade visual.
