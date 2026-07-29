# Revisão do painel — julho/2026

Registro do que foi auditado, do que estava errado e do que mudou. Serve como
justificativa das alterações e como aviso sobre leituras que o grupo pode ter
feito a partir da versão anterior.

---

## 1. Três colunas da base cartográfica não significam o que o nome sugere

Esta é a correção mais importante. A versão anterior do painel exibia números
corretos sob rótulos errados, o que leva a conclusões erradas sobre a carteira.

| Coluna | O que o painel dizia | O que a coluna é de fato |
|---|---|---|
| `AREA_MAX` | "Área máxima do lote", "Área total" | **Área máxima de construção** (potencial construtivo) |
| `AREA_CALCU` | exibida como uma área | **Coeficiente de aproveitamento** |
| `OCUPACAO` | "Ocupação" (situação) | **Taxa máxima de ocupação, em %** |
| `PERCENTUAL` | "%" ao lado da ocupação | **Repetição de `AREA_MAX`**, não é percentual |
| `Shape__Are` | não exibida | **Área do terreno** (polígono cadastral) |

### Como isso foi confirmado

Três verificações independentes, todas convergentes:

1. `PPR_a_ser_const` é **idêntica** a `AREA_MAX` nos 108 imóveis com triagem, e
   `PPR_Area_imovel` é **idêntica** a `Shape__Are` nos mesmos 108.
2. `Shape__Are × AREA_CALCU = AREA_MAX` — erro relativo mediano de 0,16%, com
   103 dos 117 casos dentro de 2%. E `AREA_CALCU` é idêntica a `PPR_CA` nos 108.
3. A Justificativa Técnica do imóvel **841600** (Polo Logístico, Lote 01) fecha
   com a base: o documento registra área máxima de construção de
   **122.663,80 m²**, coeficiente máximo **1,5** e taxa de ocupação **40%** —
   exatamente os valores de `AREA_MAX`, `AREA_CALCU` e `OCUPACAO` na base.

### Efeito prático

A métrica "Área total (m²)" da Visão geral somava **2.948.701 m²**. A área de
terreno da carteira é **2.496.975 m²**. O número anterior era a soma do
potencial construtivo — 18% maior — apresentada como se fosse terreno.

Na ficha, o campo "Ocupação · %" produzia leituras como `40.0 · 122.664%`.

### O que mudou

O painel passou a trabalhar com campos derivados de nome explícito:

- `AREA_TERRENO` (de `Shape__Are`)
- `POT_CONSTRUTIVO` (de `AREA_MAX`)
- `CA_BASE` (de `AREA_CALCU`)
- `TX_OCUP_BASE` (de `OCUPACAO`)
- `PROJECAO_MAX` (calculado: terreno × taxa de ocupação)

Área e potencial aparecem agora como métricas separadas, e um gráfico de
dispersão mostra as duas grandezas juntas — a inclinação de cada ponto é o
coeficiente de aproveitamento.

> **Ressalva que continua valendo:** a área do polígono cadastral pode divergir
> da área registrada em matrícula. No 841600 a base traz 81.887,80 m² e a
> Justificativa Técnica registra 81.775,87 m² — diferença de 0,14%. O relatório
> gerado pelo painel já sai com essa ressalva no texto.

---

## 2. As tabelas da ficha do imóvel quebravam

As tabelas eram montadas em Markdown por interpolação de texto. Como o conteúdo
da TB55 contém o caractere `|` e quebras de linha, a tabela partia ao meio e o
texto vazava para fora da célula.

Ocorrências na base atual: `TB55_ANOTACOES_PROCESSO` (1 pipe, 5 quebras de
linha), `TB55_ULT_OBSERVACAO` (2 quebras), `OBSERVACAO` da aba de observações
(1 pipe, 7 quebras).

As tabelas passaram a ser montadas em HTML com escape do conteúdo
(`nucleo.tabela_html`), o que também elimina o risco de texto da base ser
interpretado como marcação na linha do tempo de observações.

---

## 3. Correções menores

- **`requirements.txt` desatualizado.** Pedia `streamlit>=1.36`, mas o código usa
  `width="stretch"`, disponível apenas a partir da 1.49. Instalação limpa
  quebrava. Corrigido para `>=1.49`.
- **Busca por processo não funcionava.** Falhava com erro de tipo quando havia
  processo sem número (87 das 142 linhas). Além disso, os números convivem em
  três formatos na fonte — CNJ sem pontuação, SEI com pontuação e citações de
  SEI dentro das anotações. A busca agora compara apenas os dígitos, então
  `00111-00009290/2019-63` e `0011100009290201963` encontram o mesmo imóvel.
- **`FORMA_IMOV` exibida como código.** A ficha mostrava `2`. O código foi
  decodificado por comparação com `PPR_Forma do imóvel`: 1 = regular,
  2 = semirregular, 3 = irregular.
- **Aba `LUOS_Vinculacao` ignorada.** A auditoria de vinculação existia no xlsx
  e nunca era lida. Agora o status da vinculação aparece na ficha e alimenta os
  encaminhamentos sugeridos no relatório.
- **Divergência entre base e vistoria não era visível.** A triagem PPR diverge
  da base cartográfica em 21 dos 71 lotes em que as duas fontes têm informação.
  A Visão geral passou a contar esses casos e a listá-los; a ficha e o relatório
  mostram as duas leituras.
- **Colunas de tipo misto.** `LUOS_AFAST_LATERAL` (número e texto) e as taxas da
  base LUOS travavam a serialização das tabelas. Padronizadas como texto.
- **Soma de avaliação sem contexto.** Só 56 dos 125 imóveis têm laudo. A métrica
  agora informa a cobertura junto do valor.

---

## 4. Paleta institucional

A cor anterior (`#1F4E79`) não constava do manual. Aplicadas as cores oficiais:

| Cor | HEX | Pantone | Uso no painel |
|---|---|---|---|
| Verde principal | `#006D33` | 356C | Títulos, gráficos principais, cabeçalho das tabelas do Word |
| Amarelo/dourado | `#E7B000` | 110C | Pendências e situações que exigem providência |
| Azul institucional | `#00416D` | 294C | Dados cartoriais e situações de uso por terceiro |

A situação do lote virou escala com significado: verde para lote livre, dourado
para o que exige providência antes da destinação, azul para uso de terceiro
identificado.

---

## 5. Abas novas

**Relatório PPR.** Monta a Justificativa Técnica Preliminar na estrutura de 11
seções do modelo aprovado. Os quadros de identificação, parâmetros urbanísticos
e comparáveis são preenchidos a partir da carteira, com a fonte declarada; os
textos entram como rascunho editável. As condicionantes físicas são detectadas
na observação de vistoria — no 841600 o gerador identificou sozinho a linha de
alta tensão e o cercamento, as mesmas condicionantes da seção 6 do documento
original. Exporta `.docx` com a identidade institucional e `.md`.

**Base LUOS.** As 910 faixas de parâmetros em três sub-abas: consulta com
filtros, enquadramento de lote (informa RA, categoria e área; devolve o quadro
urbanístico calculado, podendo partir de um imóvel da carteira) e o log das 826
revisões, com destaque para as 11 pendências de conferência manual.

---

## 6. Verificação

- Geração de relatório executada nos **125 imóveis**, sem falhas.
- Bateria de testes de interface (`streamlit.testing`) cobrindo busca, todos os
  filtros, conjuntos de colunas, troca de imóvel, seleção vazia, imóvel sem
  triagem PPR, imóvel com coeficiente zero e o enquadramento LUOS — sem
  exceções.
- Documento Word conferido visualmente contra o modelo em PDF.
