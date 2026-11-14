# Presets de movimento

Pontos de partida para `motion.preset`. Os números são **ordens de grandeza para calibrar**, não valores certos: dependem da escala do elemento e do estilo da arte. Uma amplitude de 5 px é sutil numa imagem de 1672 px e enorme num ícone de 64 px. Prefira `fraction_of_bbox` quando a escala varia.

Um preset só vale se o efeito pretendido fizer sentido para aquele elemento. Se nenhum servir, use `"preset": "custom"` e explique em `note`.

## Sumário

- Corpo e estrutura: `bob`, `roll`
- Tecido e cabelo: `wave_distortion`, `cloth_sway`, `hair_sway`, `billow`
- Cordas e filamentos: `rope_sway`
- Água: `displace_in_mask`, `foam_surge`, `glitter`
- Luz: `flicker`, `glow_pulse`, `twinkle`
- Céu: `drift`

## Corpo e estrutura

| Preset | O que move | O que deve ficar fixo | Armadilha |
|---|---|---|---|
| `bob` | Translação vertical de toda a estrutura (navio, plataforma, criatura flutuando) | Nada dentro do corpo; filhos herdam | Dar `bob` também aos filhos soma os dois movimentos |
| `roll` | Rotação pequena em torno de um pivô | O pivô | Acima de ~1° o casco descola da linha d'água; a linha de contato precisa acompanhar |

## Tecido e cabelo

| Preset | O que move | Fixo | Armadilha |
|---|---|---|---|
| `wave_distortion` | Onda que cresce da fixação para a ponta (bandeira) | A borda presa ao mastro | Sem `attachment` confirmado, a onda nasce no lugar errado |
| `cloth_sway` | Balanço de capa ou lenço | Ombros / ponto de fixação | O corpo atrás do tecido precisa existir (`hidden_content`) |
| `hair_sway` | Balanço das mechas | A raiz na cabeça | Mechas finas sobre o fundo exigem alpha; cabelo claro sobre céu escuro gera halo na borda |
| `billow` | Inflar de vela ou cortina | Bordas presas (verga, mastro) | O sentido do vento deve concordar com bandeira e tecidos próximos |

## Cordas e filamentos

| Preset | O que move | Fixo | Armadilha |
|---|---|---|---|
| `rope_sway` | Balanço mínimo de cordame | As duas pontas | Cordas tensionadas quase não se movem; estrutura vazada arrasta o fundo sem máscara com buracos |

## Água

| Preset | O que move | Fixo | Armadilha |
|---|---|---|---|
| `displace_in_mask` | Deslocamento cíclico da superfície | Tudo que não é água (casco, personagens, lua) | Sem máscara da água, o deslocamento arrasta o navio. O contato casco/água precisa acompanhar o balanço |
| `foam_surge` | Subida e descida da espuma | A proa (a espuma a segue) | Se o navio balança e a espuma não, a espuma parece colada na imagem |
| `glitter` | Brilho do reflexo (luminosidade, não posição) | A posição do reflexo, sob a fonte de luz | Mover a posição desconecta o reflexo da lua |

## Luz

| Preset | O que move | Fixo | Armadilha |
|---|---|---|---|
| `flicker` | Brilho da chama ou janela | A posição do objeto | Exige máscara de emissão; escurecer o objeto inteiro apaga o vidro e a moldura |
| `glow_pulse` | Pulso lento de halo | A posição | Pulso forte demais lê como pisca-pisca |
| `twinkle` | Brilho de estrelas | Posição | Fases diferentes por estrela; senão piscam em bloco |

Fase (`phase`, 0 a 1) diferente por elemento evita que lanternas ou estrelas pisquem juntas.

## Céu

| Preset | O que move | Fixo | Armadilha |
|---|---|---|---|
| `drift` | Deriva lenta de nuvens | O céu ao fundo | Nuvens misturadas à nebulosa exigem máscara e reconstrução do fundo; o loop precisa fechar sem corte |

## Checagens antes de aceitar qualquer preset

1. **Contato:** o que toca esse elemento (mãos no leme, corda no mastro, casco na água) e acompanha o movimento?
2. **Tensão:** é corda esticada ou tecido solto? O esticado quase não se move.
3. **Luz e reflexo:** se o elemento emite luz, o reflexo ou o halo precisam de movimento coerente.
4. **Herança:** algum ancestral já tem esse movimento?
5. **Direção do vento:** bandeira, tecidos e velas apontam para o mesmo lado? Registre a direção inferida em `limits.notes`.
