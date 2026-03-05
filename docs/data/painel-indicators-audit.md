# Painel — Auditoria de Indicadores (ótica cidadão)

**Data:** 2026-02-28  
**Objectivo:** Identificar indicadores relevantes para o quotidiano do cidadão, hoje ausentes do Painel (dashboard `/api/resumo`).

---

## KPIs actuais no Painel (6)

| ID | Label | Source/Indicator | Ótica |
|---|---|---|---|
| `industrial_production` | Produção Industrial | INE/ipi_seasonal_cae_TOT | Indústria |
| `unemployment` | Desemprego | OECD/unemp_m | **Cidadão** ✓ |
| `inflation` | Inflação | INE/hicp_yoy | **Cidadão** ✓ |
| `energy_cost` | Custo Energia | REN/electricity_price_mibel | Indústria (MIBEL) |
| `industrial_employment` | Emprego Industrial | INE/emp_industry_cae | Indústria |
| `confidence` | Confiança Industrial | INE/conf_manufacturing | Indústria |

**Análise:**
- **4/6 indicadores** são focados na indústria (produção, emprego, confiança, energia MIBEL)
- **2/6 indicadores** têm relevância directa para o cidadão (desemprego, inflação)
- **Foco actual:** conjuntura industrial e empresarial
- **Foco em falta:** poder de compra, custo de vida, crédito, habitação

---

## Indicadores na DB mas ausentes do Painel

### A. Custo de Vida e Energia (ótica doméstica)

| Source/Indicator | Label | Unit | Recomendação |
|---|---|---|---|
| `DGEG/price_diesel` | Preço Gasóleo | €/l | **Alta** — custo transporte e famílias |
| `DGEG/price_gasoline_95_pvp` | Preço Gasolina 95 | €/l | **Alta** — custo mobilidade quotidiana |
| `ERSE/btn_simple` | Tarifa BTN Simples | €/kWh | **Alta** — custo electricidade doméstica (vs MIBEL industrial) |
| `DGEG/industrial_band_ic_incl_taxes` | Electricidade Industrial (IC) | €/kWh | Média — comparação indústria/doméstico |

**Justificação:**  
Os preços dos combustíveis e a tarifa doméstica de electricidade afectam directamente o orçamento familiar. O Painel actual mostra o preço MIBEL (mercado grossista), irrelevante para o consumidor final.

---

### B. Crédito e Financiamento

| Source/Indicator | Label | Unit | Recomendação |
|---|---|---|---|
| `BPORTUGAL/euribor_12m` | Euribor 12 meses | % | **Muito Alta** — indexante de crédito habitação |
| `BPORTUGAL/euribor_3m` | Euribor 3 meses | % | Alta — indexante alternativo |
| `BPORTUGAL/credit_housing` | Crédito à Habitação (stock) | M€ | Média — endividamento total |
| `BPORTUGAL/credit_consumer` | Crédito ao Consumo (stock) | M€ | Média — endividamento famílias |
| `BPORTUGAL/spread_pt_de` | Spread Portugal-Alemanha | p.b. | Baixa — indicador macro, pouco intuitivo para cidadão |

**Justificação:**  
A Euribor 12m é o **indexante dominante** do crédito habitação em Portugal. Com ~2,5M de portugueses com empréstimo para casa, a Euribor afecta directamente a prestação mensal. É **o indicador financeiro mais relevante para o cidadão** após a inflação.

---

### C. Salários e Poder de Compra

| Source/Indicator | Label | Unit | Recomendação |
|---|---|---|---|
| `INE/wages_industry_cae` | Salários na Indústria | Índice 2021=100 | Média — limitado ao sector industrial, formato índice |

**Justificação:**  
O indicador existe mas é **insuficiente**:
- Apenas cobre a **indústria** (~20% do emprego)
- Formato **índice** (não €), pouco intuitivo para o cidadão
- Não ajusta pela inflação (salário nominal vs real)

**Gap crítico:** Falta indicador de **salário médio nacional** em euros e **salário real** (poder de compra).

---

### D. Commodities e Alimentação

| Source/Indicator | Label | Unit | Recomendação |
|---|---|---|---|
| `FRED/wheat` | Trigo | USD/bushel | Baixa — preço internacional, pouco directo |
| `FRED/corn` | Milho | USD/bushel | Baixa |
| `FRED/coffee` | Café | USD/lb | Baixa |
| `FRED/brent_oil` | Petróleo Brent | USD/bbl | Média — afecta combustíveis, mas indirecto |

**Justificação:**  
Os preços internacionais de commodities **afectam a inflação alimentar**, mas são indicadores **indirectos**. O cidadão sente o impacto via **cesta de compras** (IHPC), já presente no Painel. Incluir commodities seria **duplicação** sem valor acrescentado para o cidadão.

---

### E. Habitação (parcial)

| Source/Indicator | Label | Unit | Recomendação |
|---|---|---|---|
| *(nenhum)* | — | — | **Gap crítico** — falta Índice de Preços da Habitação |

**Justificação:**  
O stock de crédito habitação existe na DB, mas **falta o preço das casas**. O INE publica o **Índice de Preços da Habitação (IPHab)** trimestralmente — indicador essencial para avaliar acessibilidade habitacional.

---

## Indicadores a recolher (não na DB)

| Indicador | Fonte | URL | Frequência | Prioridade |
|---|---|---|---|---|
| **Taxa média crédito habitação** | Banco de Portugal — Estatísticas de crédito | [BPstat — Taxas de juro](https://bpstat.bportugal.pt/serie/12688208) | Mensal | **Muito Alta** |
| **Índice de Preços da Habitação (IPHab)** | INE — Índice de Preços da Habitação | [INE — IPHab](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0011208) | Trimestral | **Muito Alta** |
| **Salário médio mensal (bruto)** | INE — Inquérito aos Ganhos e Duração do Trabalho | [INE — Ganhos](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0001069) | Anual | **Alta** |
| **Inflação core (excl. energia e alimentação)** | INE — IHPC subjacente | [INE — IHPC core](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0008601) | Mensal | Alta |
| **Taxa de poupança das famílias** | INE — Contas Nacionais Trimestrais | [INE — CNT](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_cnacionais) | Trimestral | Média |
| **Confiança do consumidor** | INE — Inquérito de Conjuntura aos Consumidores | [INE — ICC](https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_indicadores&indOcorrCod=0008495) | Mensal | Média |
| **Salário real (poder de compra)** | Calculado: `wages_nominal / IHPC` | — | Mensal (após recolher wage nominal) | **Alta** |

**Notas técnicas:**
- **Taxa crédito habitação:** série `12688208` no BPstat — taxa média ponderada novos contratos, habitação própria permanente
- **IPHab:** série trimestral, índice 2015=100, cobre preços de transacção (não avaliação bancária)
- **Salário médio:** INE só publica anualmente via inquérito aos ganhos; dado **não está disponível em frequência mensal**
- **Inflação core:** IHPC excluindo produtos energéticos e alimentares não transformados (volatilidade alta)

---

## Recomendação: novos KPIs para o Painel (top 6)

### 1. **Euribor 12 meses** (já na DB: `BPORTUGAL/euribor_12m`)
- **Porquê:** Afecta directamente a prestação mensal de ~2,5M de portugueses com crédito habitação
- **Formato:** `X.XX%` + variação anual em pp
- **Contexto:** "Subiu 0.3 pp face ao ano anterior — prestação de €800/mês sobe ~€24"

### 2. **Taxa média crédito habitação** (a recolher: BdP série 12688208)
- **Porquê:** Taxa efectiva paga nos novos contratos (Euribor + spread bancário)
- **Formato:** `X.XX%` + variação anual
- **Contexto:** "Taxa média novos contratos: 4.2% (Euribor 3.1% + spread 1.1%)"

### 3. **Preço combustíveis** (já na DB: `DGEG/price_diesel` ou `price_gasoline_95_pvp`)
- **Porquê:** Mobilidade quotidiana — afecta orçamento familiar e transportes
- **Formato:** `€X.XXX/litro` + variação mensal
- **Contexto:** "Gasóleo: €1.652/l (↑ €0.05 vs mês anterior)"
- **Decisão:** Mostrar **gasóleo** (mais representativo: comerciais + parte das famílias)

### 4. **Tarifa electricidade doméstica** (já na DB: `ERSE/btn_simple`)
- **Porquê:** Custo electricidade para famílias (vs MIBEL industrial actual)
- **Formato:** `€X.XXXX/kWh` + variação semestral/anual
- **Contexto:** "Tarifa BTN: €0.1842/kWh (família média 200 kWh/mês = €36.84)"

### 5. **Índice de Preços da Habitação** (a recolher: INE IPHab)
- **Porquê:** Acessibilidade habitacional — problema estrutural em Portugal
- **Formato:** `Índice 2015=100` + variação anual
- **Contexto:** "Preços habitação: 145.2 (↑ 8.3% vs ano anterior)"
- **Limitação:** Trimestral (não mensal)

### 6. **Salário real / Poder de compra** (a recolher: wage nominal + calcular)
- **Porquê:** Indicador-síntese do nível de vida — salário ajustado pela inflação
- **Formato:** `Índice 2021=100` + variação anual
- **Contexto:** "Poder de compra: 98.5 (↓ 1.5% vs ano anterior — salários não acompanham inflação)"
- **Limitação:** INE só publica salários **anualmente** (inquérito aos ganhos)
- **Alternativa curto prazo:** Mostrar `INE/wages_industry_cae` ajustado pela inflação (apenas indústria)

---

## Painel proposto (8 KPIs = 2 industrial + 6 cidadão)

### Bloco A: Macro Cidadão (6)
1. **Desemprego** (mantém actual)
2. **Inflação** (mantém actual)
3. **Euribor 12m** (novo — crédito habitação)
4. **Preço Gasóleo** (novo — mobilidade)
5. **Tarifa Electricidade BTN** (novo — energia doméstica)
6. **Índice Preços Habitação** (novo — acessibilidade)

### Bloco B: Indústria (2 — mantém foco CAE)
7. **Produção Industrial** (mantém)
8. **Confiança Industrial** (mantém)

**Racional:**  
- Equilibra **ótica cidadão** (6 KPIs) com **ótica industrial** (2 KPIs) relevante para a CAE
- Remove `energy_cost MIBEL` (irrelevante para cidadão) → substitui por `tarifa BTN`
- Remove `industrial_employment` (redundante com unemployment + production)
- Mantém desemprego e inflação (já são ótica cidadão)
- Adiciona **4 novos KPIs críticos:** Euribor, combustível, electricidade, habitação

---

## Alternativa: Painel Híbrido (mantém 6 KPIs)

Se João preferir **manter 6 KPIs** mas reorientar para cidadão:

1. **Desemprego** (mantém)
2. **Inflação** (mantém)
3. **Euribor 12m** (novo — substitui `spread_pt_de`)
4. **Preço Gasóleo** (novo — substitui `energy_cost MIBEL`)
5. **Produção Industrial** (mantém — relevância CAE)
6. **Confiança Industrial** (mantém — expectativas económicas)

**Racional:**  
- Mantém estrutura 6 KPIs actual
- 4 cidadão (unemployment, inflation, euribor, fuel) + 2 indústria (production, confidence)
- Substitui indicadores MIBEL/employment industrial por indicadores quotidianos

---

## Próximos Passos

1. **Decisão João:** Painel 8 KPIs (6 cidadão + 2 indústria) ou 6 KPIs híbrido?
2. **Recolha dados em falta:**
   - Taxa crédito habitação (BdP série 12688208) — script `collectors/bportugal_mortgage_rate.py`
   - Índice Preços Habitação (INE IPHab) — script `collectors/ine_housing_prices.py`
   - Inflação core (INE IHPC subjacente) — extensão `collectors/ine.py`
3. **Actualizar `resumo.py`:**
   - Adicionar novos KPIs seleccionados
   - Ajustar lógica de contexto para indicadores financeiros (Euribor, taxas)
4. **UI/UX:**
   - Verificar se layout suporta 8 cards ou manter 6
   - Adicionar tooltip explicativo para indicadores técnicos (Euribor, IPHab)

---

## Apêndice: Catálogo Completo (72 indicadores)

**BPORTUGAL (11):** euribor_1m, euribor_3m, euribor_6m, euribor_12m, pt_10y, de_10y, spread_pt_de, credit_housing, credit_consumer, deposits, eur_usd  
**DGEG (17):** gross_production_total, gross_production_wind, gross_production_hydro, gross_production_solar_pv, total_consumption, net_imports, energy_dependence, renewable_share_electricity, renewable_share_total, energy_intensity, co2_emissions_total, price_diesel, price_gasoline_95_pvp, natgas_price_industry_€_per_MWh, industrial_band_ic_incl_taxes, brent_usd  
**ERSE (5):** tariff_mt_peak, tariff_mt_off_peak, tariff_at_peak, tariff_mat_peak, btn_simple  
**EUROSTAT (10):** ipi, manufacturing, total_industry, metals, chemicals_pharma, machinery, transport_eq, rubber_plastics, inflation, unemployment  
**FRED (7):** brent_oil, natural_gas, copper, aluminum, wheat, corn, coffee  
**INE (6):** ipi_seasonal_cae, ipi_yoy_cae, emp_industry_cae, wages_industry_cae, conf_manufacturing, hicp_yoy  
**OECD (6):** cli, production, order_books, selling_prices, employment, unemp_m  
**REN (10):** electricity_price_mibel, electricity_hydro, electricity_wind, electricity_solar, electricity_natural_gas, electricity_biomass, electricity_consumption, electricity_production_total, electricity_production_renewable, electricity_net_imports  
**WORLDBANK (3):** birth_rate, rnd_pct_gdp, fdi_inflows_pct_gdp  

**Total:** 72 indicadores disponíveis na base de dados  
**Usados no Painel actual:** 6 (8.3% do catálogo)
