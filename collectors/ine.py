#!/usr/bin/env python3
"""
INE (Instituto Nacional de Estatística) API Client - Dados Oficiais Portugal
API JSON - Sem autenticação
Portal: https://www.ine.pt/xportal/xmain?xpid=INE&xpgid=ine_api_v2
Catálogo: https://dados.gov.pt/en/datasets/?organization=instituto-nacional-de-estatistica

Notas sobre a API:
- Sem Dim1, retorna apenas o período mais recente
- Dim1=T retorna todos os períodos (pode ser lento para séries longas)
- Períodos mensais: S3A{YYYYMM} (ex: S3A202501 = Janeiro 2025)
- Períodos trimestrais: S7A{YYYY}{Q} (ex: S7A20251 = Q1 2025)
- Períodos anuais: S7A{YYYY} (ex: S7A2025)
- Chaves no JSON são nomes portugueses ("Janeiro de 2025"), NÃO S3A codes
"""

import requests
from typing import Optional, Dict, List, Union
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Mapeamento meses PT → número (para ordenação cronológica)
_PT_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}

# Trimestres PT → (mês_início, mês_fim)
_PT_QUARTERS = {
    "1.º trimestre": (1, 3), "2.º trimestre": (4, 6),
    "3.º trimestre": (7, 9), "4.º trimestre": (10, 12),
}


def _period_sort_key(period_name: str) -> str:
    """
    Converte nome de período PT para chave ordenável (YYYY-MM).
    Exemplos:
        "Janeiro de 2025" → "2025-01"
        "Dezembro de 2025" → "2025-12"
        "3.º Trimestre de 2025" → "2025-07"
        "2024" → "2024-00"
    """
    lower = period_name.lower().strip()

    # Mensal: "janeiro de 2025"
    for month_name, month_num in _PT_MONTHS.items():
        if lower.startswith(month_name):
            parts = lower.split()
            year = parts[-1]
            return f"{year}-{month_num:02d}"

    # Trimestral: "1.º trimestre de 2025"
    for q_name, (m_start, _) in _PT_QUARTERS.items():
        if q_name in lower:
            parts = lower.split()
            year = parts[-1]
            return f"{year}-{m_start:02d}"

    # Anual: "2025"
    if lower.isdigit() and len(lower) == 4:
        return f"{lower}-00"

    # Fallback: usar string original
    return period_name


def _generate_monthly_codes(months: int, ref_date: Optional[datetime] = None) -> List[str]:
    """Gerar lista de S3A codes para últimos N meses"""
    if ref_date is None:
        ref_date = datetime.now()
    codes = []
    for i in range(months):
        dt = ref_date - relativedelta(months=i)
        codes.append(f"S3A{dt.year}{dt.month:02d}")
    return list(reversed(codes))


def _generate_quarterly_codes(quarters: int, ref_date: Optional[datetime] = None) -> List[str]:
    """Gerar lista de S7A codes para últimos N trimestres"""
    if ref_date is None:
        ref_date = datetime.now()
    codes = []
    year = ref_date.year
    quarter = (ref_date.month - 1) // 3 + 1
    for i in range(quarters):
        codes.append(f"S7A{year}{quarter}")
        quarter -= 1
        if quarter == 0:
            quarter = 4
            year -= 1
    return list(reversed(codes))


def _generate_annual_codes(years: int, ref_date: Optional[datetime] = None) -> List[str]:
    """Gerar lista de S7A codes para últimos N anos"""
    if ref_date is None:
        ref_date = datetime.now()
    return [f"S7A{ref_date.year - i}" for i in range(years - 1, -1, -1)]


class INEClient:
    """Cliente para INE Portugal JSON API"""

    # Endpoints
    DATA_URL = "https://www.ine.pt/ine/json_indicador/pindica.jsp"
    META_URL = "https://www.ine.pt/ine/json_indicador/pindicaMeta.jsp"

    # === INDICADORES PRINCIPAIS (Base 2021 salvo indicação) ===

    # Produção Industrial (IPI) - Mensal
    IPI = {
        "ipi_bruto_cae":          "0011885",  # IPI bruto por CAE Rev.3
        "ipi_bruto_mig":          "0011884",  # IPI bruto por Agrupamento Industrial (MIG)
        "ipi_adjusted_cae":       "0011887",  # IPI ajustado calendário por CAE Rev.3
        "ipi_adjusted_mig":       "0011886",  # IPI ajustado calendário por Agrupamento
        "ipi_seasonal_cae":       "0011889",  # IPI ajustado calendário+sazonalidade por CAE Rev.3
        "ipi_yoy_cae":            "0011897",  # IPI bruto variação homóloga (%) por CAE
        "ipi_yoy_mig":            "0011896",  # IPI bruto variação homóloga (%) por Agrupamento
        "ipi_mom_cae":            "0011891",  # IPI bruto variação mensal (%) por CAE
        "ipi_mom_mig":            "0011890",  # IPI bruto variação mensal (%) por Agrupamento
        "ipi_avg_annual_cae":     "0011907",  # IPI variação média anual (%) por CAE
    }

    # Volume de Negócios na Indústria - Mensal
    TURNOVER = {
        "turnover_total_cae":     "0011908",  # VN total por CAE Rev.3
        "turnover_total_mig":     "0011948",  # VN total por Agrupamento
        "turnover_internal_cae":  "0011909",  # VN mercado interno por CAE
        "turnover_external_cae":  "0011910",  # VN mercado externo por CAE
        "turnover_yoy_cae":       "0011968",  # VN variação homóloga (%) por CAE
        "turnover_mom_cae":       "0011978",  # VN variação mensal (%) por CAE
    }

    # Preços na Produção Industrial (IPPI) - Mensal
    IPPI = {
        "ippi_total_cae":         "0011988",  # IPPI total por CAE Rev.3
        "ippi_internal_cae":      "0011989",  # IPPI mercado interno por CAE
        "ippi_external_cae":      "0011990",  # IPPI mercado externo por CAE
        "ippi_total_mig":         "0011991",  # IPPI por mercado × Agrupamento
        "ippi_yoy_mig":           "0011993",  # IPPI variação homóloga (%) por Agrupamento
        "ippi_yoy_cae":           "0012002",  # IPPI variação homóloga (%) por CAE
    }

    # Emprego e Salários na Indústria - Mensal
    EMPLOYMENT = {
        "emp_industry_cae":       "0011912",  # Índice emprego indústria por CAE
        "emp_industry_mig":       "0011952",  # Índice emprego indústria por Agrupamento
        "wages_industry_cae":     "0011911",  # Índice remunerações indústria por CAE
        "hours_industry_mig":     "0011953",  # Índice horas trabalhadas por Agrupamento
        "emp_yoy_cae":            "0011972",  # Emprego variação homóloga (%) por CAE
        "emp_mom_cae":            "0011942",  # Emprego variação mensal (%) por CAE
    }

    # Construção - Mensal
    CONSTRUCTION = {
        "constr_prod_cae":        "0011741",  # Produção construção por CAE
        "constr_prod_type":       "0011769",  # Produção construção por tipo obra
        "constr_emp_cae":         "0011745",  # Emprego construção por CAE
        "constr_wages_cae":       "0011744",  # Remunerações construção por CAE
        "constr_cost":            "0011748",  # Índice custo construção
        "constr_cost_yoy":        "0011750",  # Custo construção variação homóloga (%)
    }

    # Indicadores Macro
    MACRO = {
        # PIB (Trimestral)
        "gdp_current":            "0013428",  # PIB preços correntes (Base 2021, EUR)
        "gdp_yoy":                "0013431",  # PIB volume variação homóloga (%)
        "gdp_per_capita_yoy":     "0013493",  # PIB real per capita variação anual (%)
        # Preços (Mensal)
        "ipc_index":              "0002384",  # IPC índice (Base 2012) por agregado
        "ipc_yoy":                "0002386",  # IPC variação homóloga (%) por agregado
        "ipc_12m_avg":            "0002390",  # IPC variação média 12 meses (%)
        "hicp_yoy":               "0000110",  # IHPC variação homóloga (Base 2015, %)
        "hicp_12m_avg":           "0000111",  # IHPC variação média 12 meses (%)
        # Desemprego (Trimestral)
        "unemployment":           "0010704",  # Taxa desemprego (Série 2021, %)
        "unemployment_annual":    "0012173",  # Taxa desemprego (%) - Anual
        # Emprego geral
        "employed_sector":        "0010679",  # Pop. empregada por setor (Trimestral)
        "employed_cae_annual":    "0014550",  # Pop. empregada por CAE Rev.3 (Anual)
        "active_population":      "0010654",  # Pop. ativa (Série 2021, Nº)
    }

    # Comércio Internacional
    TRADE = {
        "exports":                "0000012",  # Exportações (EUR) mensal
        "imports":                "0005715",  # Importações (EUR) mensal
        "exports_by_goods":       "0005720",  # Exportações por destino e NC8 - Anual
        "trade_openness":         "0014134",  # Grau de abertura (%)
    }

    # Confiança e Clima Económico - Mensal
    CONFIDENCE = {
        "economic_climate":       "0014334",  # Indicador clima económico
        "economic_climate_3m":    "0001222",  # Clima económico (média 3 meses)
        "conf_manufacturing":     "0001188",  # Confiança indústria transformadora
        "conf_manufacturing_sa":  "0014332",  # Confiança indústria (dessazonalizado)
        "conf_construction":      "0000147",  # Confiança construção
        "conf_trade":             "0001163",  # Confiança comércio
        "conf_services":          "0001214",  # Confiança serviços
        "conf_consumers":         "0001173",  # Confiança consumidores
        "capacity_utilization":   "0001191",  # Utilização capacidade produtiva (%) - Trimestral
        "export_outlook":         "0001192",  # Perspetivas exportação
        "order_book":             "0001193",  # Apreciação carteira encomendas
    }

    # Salários e Custos Trabalho
    WAGES = {
        "avg_monthly_earnings":   "0001226",  # Ganho médio mensal (EUR) por CAE - Anual
        "base_remuneration":      "0006910",  # Remuneração média mensal base - Anual
        "labour_cost_index":      "0011798",  # Índice custo trabalho (Base 2020) - Trimestral
        "labour_cost_yoy":        "0011804",  # ICT variação homóloga (%)
    }

    # Energia (Anual - INE só tem anuais)
    ENERGY = {
        "electricity_consumption": "0008222",  # Consumo eletricidade (kWh) - Anual
        "final_energy":            "0002010",  # Consumo final energia (tep) - Anual
        "primary_energy":          "0002103",  # Consumo primário energia (tep) - Anual
        "renewable_share":         "0009798",  # Quota renováveis no consumo final (%) - Anual
    }

    # Mapeamento CAE Rev.3 para divisões industriais
    # NOTA: INE usa códigos de divisão individuais (24, 25, 28), NÃO grupos
    # como Eurostat (C24_25). Para obter agregados, pedir divisões separadas.
    CAE_SECTORS = {
        "total":                "TOT",
        "extractive":           "B",
        "manufacturing":        "C",
        "utilities":            "D",
        "water_waste":          "E",
        # Divisões individuais (CAE Rev.3)
        "food":                 "10",       # Indústrias alimentares
        "beverages":            "11",       # Bebidas
        "textiles":             "13",       # Fabricação de têxteis
        "clothing":             "14",       # Indústria do vestuário
        "leather":              "15",       # Couro e produtos do couro
        "wood_cork":            "16",       # Madeira e cortiça
        "paper":                "17",       # Pasta, papel, cartão
        "printing":             "18",       # Impressão
        "petroleum":            "19",       # Coque, produtos petrolíferos refinados
        "chemicals":            "20",       # Produtos químicos
        "pharma":               "21",       # Produtos farmacêuticos
        "rubber_plastics":      "22",       # Borracha e plásticos
        "minerals":             "23",       # Outros produtos minerais não metálicos
        "basic_metals":         "24",       # Metalurgia de base (CAE focus)
        "metal_products":       "25",       # Produtos metálicos (CAE focus)
        "electronics":          "26",       # Equipamentos informáticos/eletrónicos
        "electrical":           "27",       # Equipamento elétrico
        "machinery":            "28",       # Máquinas e equipamentos (CAE focus)
        "vehicles":             "29",       # Veículos automóveis
        "other_transport":      "30",       # Outro equipamento de transporte
        "furniture":            "31",       # Mobiliário e colchões
        "other_manufacturing":  "32",       # Outras indústrias transformadoras
        "repair_install":       "33",       # Reparação e instalação de máquinas
    }

    # Mapeamento MIG (Main Industrial Groupings)
    MIG_GROUPS = {
        "total":                "TOT",
        "intermediate_goods":   "ING",
        "capital_goods":        "CAG",
        "consumer_goods":       "COG",
        "durable_consumer":     "DCOG",
        "nondurable_consumer":  "NDCOG",
        "energy":               "ENG",
    }

    def __init__(self, lang: str = "PT"):
        self.lang = lang
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "OpenClaw Economic Data Collector"
        })

    def _resolve_varcd(self, indicator: str) -> str:
        """Resolver alias para código varcd"""
        for group in [self.IPI, self.TURNOVER, self.IPPI, self.EMPLOYMENT,
                      self.CONSTRUCTION, self.MACRO, self.TRADE,
                      self.CONFIDENCE, self.WAGES, self.ENERGY]:
            if indicator in group:
                return group[indicator]
        if indicator.isdigit() and len(indicator) == 7:
            return indicator
        raise ValueError(f"Indicador desconhecido: {indicator}")

    def _parse_response(self, data: dict, indicator: str, varcd: str,
                        cae_filter: Optional[str] = None,
                        aggregate_filter: Optional[str] = None) -> Dict:
        """
        Parsear resposta INE e devolver dados normalizados.

        A API INE devolve:
        {
            "Dados": {
                "Janeiro de 2025": [
                    {"geocod": "PT", "dim_3": "C", "dim_3_t": "...", "valor": "94.84", ...},
                    ...
                ],
                ...
            }
        }
        """
        record = data[0] if isinstance(data, list) else data

        if "Erro" in record or "erro" in record:
            return {
                "error": record.get("Erro", record.get("erro", "Unknown error")),
                "indicator": indicator, "varcd": varcd
            }

        observations = []
        dados = record.get("Dados", {})

        for period_key, values in dados.items():
            if not isinstance(values, list):
                continue

            sort_key = _period_sort_key(period_key)

            for entry in values:
                # Filtro CAE: verificar dim_3 (ou dim_2 para alguns indicadores)
                if cae_filter:
                    entry_cae = entry.get("dim_3", entry.get("dim_2", ""))
                    if entry_cae != cae_filter:
                        continue

                # Filtro agregado (para IPC/HICP que têm múltiplas categorias)
                if aggregate_filter:
                    for k, v in entry.items():
                        if k.startswith("dim_") and k.endswith("_t"):
                            continue
                        if k.startswith("dim_") and v == aggregate_filter:
                            break
                    else:
                        # Nenhuma dimensão correspondeu
                        pass  # não filtrar se não houver match explícito

                # Converter valor
                raw_value = entry.get("valor")
                value = None
                if raw_value is not None and raw_value != "":
                    try:
                        value = float(raw_value)
                    except (ValueError, TypeError):
                        value = raw_value

                obs = {
                    "period": period_key,
                    "period_sort": sort_key,
                    "value": value,
                    "status": entry.get("sinal_conv", ""),
                }

                # Adicionar labels de dimensão
                for k, v in entry.items():
                    if k.startswith("dim_") and k.endswith("_t"):
                        obs[k] = v
                    elif k.startswith("dim_") and not k.endswith("_t"):
                        obs[k] = v
                    elif k == "geocod":
                        obs["geo"] = v
                    elif k == "geodsg":
                        obs["geo_name"] = v

                observations.append(obs)

        # Ordenar cronologicamente
        observations.sort(key=lambda x: x["period_sort"])

        return {
            "indicator": indicator,
            "varcd": varcd,
            "name": record.get("IndicadorDsg", ""),
            "last_update": record.get("DataUltimoAtualizacao", ""),
            "last_period": record.get("UltimoPref", ""),
            "count": len(observations),
            "data": observations,
            "source": "INE Portugal",
            "url": f"https://www.ine.pt/xurl/indx/{varcd}/PT"
        }

    def get_metadata(self, indicator: str) -> Dict:
        """Obter metadados de um indicador (dimensões, períodos, unidades)"""
        varcd = self._resolve_varcd(indicator)
        try:
            response = self.session.get(
                self.META_URL,
                params={"varcd": varcd, "lang": self.lang},
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return {"error": f"Sem metadados para {varcd}", "indicator": indicator}

            meta = data[0] if isinstance(data, list) else data
            return {
                "indicator": indicator,
                "varcd": varcd,
                "name": meta.get("IndicadorNome", ""),
                "periodicity": meta.get("Periodic", ""),
                "first_period": meta.get("PrimeiroPeriodo", ""),
                "last_period": meta.get("UltimoPeriodo", ""),
                "unit": meta.get("UnidadeMedida", ""),
                "last_update": meta.get("DataUltimaAtualizacao", ""),
                "dimensions": meta.get("Dimensoes", []),
                "source": "INE Portugal",
            }
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "indicator": indicator}
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return {"error": f"Parse error: {str(e)}", "indicator": indicator}

    def get_data(
        self,
        indicator: str,
        months: Optional[int] = None,
        quarters: Optional[int] = None,
        years: Optional[int] = None,
        periods: Optional[Union[str, List[str]]] = None,
        cae: Optional[str] = None,
        dim_filters: Optional[Dict[str, str]] = None,
        ref_date: Optional[datetime] = None
    ) -> Dict:
        """
        Obter dados de um indicador.

        Args:
            indicator: Alias ou varcd code
            months: Últimos N meses (gera S3A codes automaticamente)
            quarters: Últimos N trimestres (gera S7A codes)
            years: Últimos N anos (gera S7A codes)
            periods: Codes manuais - 'T' para todos, ou lista de S3A/S7A codes
            cae: Filtrar por setor CAE (alias de CAE_SECTORS ou código direto)
            dim_filters: Filtros dimensionais extras {'Dim2': 'PT', 'Dim3': 'C'}

        Nota: A API INE rejeita o pedido inteiro se QUALQUER código Dim1 não
        existir. Este método faz fallback automático para Dim1=T (todos os
        períodos) com filtragem client-side quando isso acontece.
        """
        varcd = self._resolve_varcd(indicator)

        params = {"op": "2", "varcd": varcd, "lang": self.lang}

        # Determinar quantos períodos recentes queremos (para fallback)
        n_recent = None

        # Gerar códigos temporais
        if periods:
            if isinstance(periods, list):
                params["Dim1"] = ",".join(periods)
            else:
                params["Dim1"] = periods
        elif months:
            codes = _generate_monthly_codes(months, ref_date=ref_date)
            params["Dim1"] = ",".join(codes)
            n_recent = months
        elif quarters:
            codes = _generate_quarterly_codes(quarters, ref_date=ref_date)
            params["Dim1"] = ",".join(codes)
            n_recent = quarters
        elif years:
            codes = _generate_annual_codes(years, ref_date=ref_date)
            params["Dim1"] = ",".join(codes)
            n_recent = years
        # Sem filtro temporal → API retorna apenas último período

        # Filtro CAE via parâmetro API
        if cae:
            cae_code = self.CAE_SECTORS.get(cae, cae)
            if dim_filters is None:
                dim_filters = {}
            if "Dim3" not in dim_filters:
                dim_filters["Dim3"] = cae_code

        if dim_filters:
            params.update(dim_filters)

        try:
            response = self.session.get(
                self.DATA_URL, params=params, timeout=120
            )
            response.raise_for_status()
            data = response.json()

            if not data:
                return {"error": "Resposta vazia", "indicator": indicator, "varcd": varcd}

            # Verificar se API rejeitou por códigos inválidos
            record = data[0] if isinstance(data, list) else data
            sucesso = record.get("Sucesso", {})
            if "Falso" in sucesso:
                # Fallback: pedir todos os períodos e filtrar client-side
                params["Dim1"] = "T"
                response = self.session.get(
                    self.DATA_URL, params=params, timeout=120
                )
                response.raise_for_status()
                data = response.json()

                if not data:
                    return {"error": "Resposta vazia (fallback)", "indicator": indicator, "varcd": varcd}

            result = self._parse_response(data, indicator, varcd)

            # Se fizemos fallback, limitar aos últimos N períodos
            # respeitando ref_date como teto (para não devolver dados futuros)
            if n_recent and "data" in result and result["data"]:
                # Períodos únicos ordenados cronologicamente
                unique_periods = []
                seen = set()
                for obs in result["data"]:
                    sk = obs["period_sort"]
                    if sk not in seen:
                        seen.add(sk)
                        unique_periods.append(sk)
                unique_periods.sort()

                # Se ref_date foi fornecido, filtrar períodos <= ref_date
                if ref_date:
                    ref_ceiling = ref_date.strftime("%Y-%m")
                    unique_periods = [p for p in unique_periods if p <= ref_ceiling]

                recent = set(unique_periods[-n_recent:])
                result["data"] = [
                    obs for obs in result["data"]
                    if obs["period_sort"] in recent
                ]
                result["count"] = len(result["data"])

            return result

        except requests.exceptions.RequestException as e:
            return {"error": str(e), "indicator": indicator, "varcd": varcd}
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return {"error": f"Parse error: {str(e)}", "indicator": indicator, "varcd": varcd}

    # === Métodos Convenientes ===

    def get_ipi(self, cae: str = "manufacturing", months: int = 13,
                adjusted: bool = True, ref_date: Optional[datetime] = None) -> Dict:
        """
        Índice de Produção Industrial Portugal.

        Args:
            cae: Setor CAE (ver CAE_SECTORS). Default: manufacturing (C)
            months: Meses de histórico
            adjusted: True=ajustado sazonalidade, False=bruto
            ref_date: Reference date for period calculation (default: now)
        """
        indicator = "ipi_seasonal_cae" if adjusted else "ipi_bruto_cae"
        return self.get_data(indicator, months=months, cae=cae, ref_date=ref_date)

    def get_ipi_yoy(self, cae: str = "manufacturing", months: int = 13,
                    ref_date: Optional[datetime] = None) -> Dict:
        """IPI variação homóloga (%) por CAE"""
        return self.get_data("ipi_yoy_cae", months=months, cae=cae, ref_date=ref_date)

    def get_hicp(self, months: int = 13, ref_date: Optional[datetime] = None) -> Dict:
        """IHPC variação homóloga (%) - Total (todos os itens)"""
        return self.get_data("hicp_yoy", months=months,
                             dim_filters={"Dim3": "T"}, ref_date=ref_date)

    def get_ipc(self, months: int = 13, ref_date: Optional[datetime] = None) -> Dict:
        """IPC variação homóloga (%) - Total"""
        return self.get_data("ipc_yoy", months=months,
                             dim_filters={"Dim3": "T"}, ref_date=ref_date)

    def get_gdp(self, quarters: int = 8, ref_date: Optional[datetime] = None) -> Dict:
        """PIB variação homóloga volume (%) - Trimestral"""
        return self.get_data("gdp_yoy", quarters=quarters, ref_date=ref_date)

    def get_gdp_current(self, quarters: int = 8, ref_date: Optional[datetime] = None) -> Dict:
        """PIB a preços correntes (EUR) - Trimestral"""
        return self.get_data("gdp_current", quarters=quarters, ref_date=ref_date)

    def get_unemployment(self, quarters: int = 8, ref_date: Optional[datetime] = None) -> Dict:
        """Taxa de desemprego (%) - Portugal total, ambos sexos - Trimestral"""
        return self.get_data("unemployment", quarters=quarters,
                             dim_filters={"Dim2": "PT", "Dim3": "T"}, ref_date=ref_date)

    def get_confidence(self, sector: str = "manufacturing", months: int = 13,
                       ref_date: Optional[datetime] = None) -> Dict:
        """
        Indicador de confiança.

        Args:
            sector: 'manufacturing', 'construction', 'trade', 'services',
                    'consumers', 'climate'
        """
        indicator_map = {
            "manufacturing": "conf_manufacturing",
            "construction": "conf_construction",
            "trade": "conf_trade",
            "services": "conf_services",
            "consumers": "conf_consumers",
            "climate": "economic_climate",
        }
        indicator = indicator_map.get(sector, sector)
        return self.get_data(indicator, months=months, ref_date=ref_date)

    def get_turnover(self, cae: str = "manufacturing", months: int = 13,
                     market: str = "total", ref_date: Optional[datetime] = None) -> Dict:
        """
        Volume de negócios na indústria.

        Args:
            market: 'total', 'internal', 'external'
        """
        indicator_map = {
            "total": "turnover_total_cae",
            "internal": "turnover_internal_cae",
            "external": "turnover_external_cae",
        }
        indicator = indicator_map.get(market, "turnover_total_cae")
        return self.get_data(indicator, months=months, cae=cae, ref_date=ref_date)

    def get_employment(self, cae: str = "manufacturing", months: int = 13,
                       ref_date: Optional[datetime] = None) -> Dict:
        """Índice emprego indústria por CAE"""
        return self.get_data("emp_industry_cae", months=months, cae=cae, ref_date=ref_date)

    def get_wages(self, cae: str = "manufacturing", months: int = 13,
                  ref_date: Optional[datetime] = None) -> Dict:
        """Índice remunerações indústria por CAE"""
        return self.get_data("wages_industry_cae", months=months, cae=cae, ref_date=ref_date)

    # === IEFP — Desemprego Registado (via INE API) ===

    def get_registered_unemployment(self, months: int = 13,
                                     ref_date: Optional[datetime] = None) -> Dict:
        """Desempregados inscritos nos centros de emprego (IEFP).

        Varcd 0014470 = Desempregados inscritos (n.º) por centro de emprego.
        Diferente do desemprego por inquérito (taxa oficial): este é desemprego
        registado (registos administrativos IEFP).
        """
        return self.get_data("0014470", months=months, ref_date=ref_date)

    def get_job_offers(self, months: int = 13,
                       ref_date: Optional[datetime] = None) -> Dict:
        """Ofertas de emprego recebidas nos centros de emprego (IEFP).

        Varcd 0014471 = Ofertas recebidas (n.º) por centro de emprego.
        """
        return self.get_data("0014471", months=months, ref_date=ref_date)

    def get_industrial_dashboard(self, months: int = 13,
                                 ref_date: Optional[datetime] = None) -> Dict[str, Dict]:
        """
        Dashboard completo indústria transformadora Portugal — parallel fetch.
        Retorna IPI, emprego, salários e confiança para setores-chave CAE.

        Setores CAE focus:
        - 24: Metalurgia de base
        - 25: Produtos metálicos
        - 28: Máquinas e equipamentos
        - 19: Coque, petrolíferos refinados
        - 20: Produtos químicos
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        tasks = {
            "ipi_total":                lambda: self.get_ipi(cae="total", months=months, ref_date=ref_date),
            "ipi_manufacturing":        lambda: self.get_ipi(cae="manufacturing", months=months, ref_date=ref_date),
            "ipi_basic_metals":         lambda: self.get_ipi(cae="basic_metals", months=months, ref_date=ref_date),
            "ipi_metal_products":       lambda: self.get_ipi(cae="metal_products", months=months, ref_date=ref_date),
            "ipi_machinery":            lambda: self.get_ipi(cae="machinery", months=months, ref_date=ref_date),
            "ipi_petroleum":            lambda: self.get_ipi(cae="petroleum", months=months, ref_date=ref_date),
            "ipi_chemicals":            lambda: self.get_ipi(cae="chemicals", months=months, ref_date=ref_date),
            "employment_manufacturing": lambda: self.get_employment("manufacturing", months, ref_date=ref_date),
            "wages_manufacturing":      lambda: self.get_wages("manufacturing", months, ref_date=ref_date),
            "confidence":               lambda: self.get_confidence("manufacturing", months, ref_date=ref_date),
        }

        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fn): key for key, fn in tasks.items()}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    results[key] = {"error": str(e), "indicator": key}

        return results


# === Exemplos de Uso ===
if __name__ == "__main__":
    client = INEClient()

    print("=== INE Portugal API - Teste ===\n")

    # 1. IPI Manufacturing últimos 6 meses
    print("1. IPI Indústrias Transformadoras (últimos 6 meses, ajustado):")
    ipi = client.get_ipi(cae="manufacturing", months=6)
    if "data" in ipi and ipi["data"]:
        for obs in ipi["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.2f}")
    elif "error" in ipi:
        print(f"  Erro: {ipi['error']}")
    print()

    # 2. IPI Metalurgia de base (CAE 24 - sector-chave)
    print("2. IPI Metalurgia de base (CAE 24, últimos 6 meses):")
    ipi_metals = client.get_ipi(cae="basic_metals", months=6)
    if "data" in ipi_metals and ipi_metals["data"]:
        for obs in ipi_metals["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.2f}")
    elif "error" in ipi_metals:
        print(f"  Erro: {ipi_metals['error']}")
    print()

    # 2b. IPI Máquinas e equipamentos (CAE 28 - sector-chave)
    print("2b. IPI Máquinas e equipamentos (CAE 28, últimos 6 meses):")
    ipi_mach = client.get_ipi(cae="machinery", months=6)
    if "data" in ipi_mach and ipi_mach["data"]:
        for obs in ipi_mach["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.2f}")
    elif "error" in ipi_mach:
        print(f"  Erro: {ipi_mach['error']}")
    print()

    # 3. IHPC (inflação total, últimos 6 meses)
    print("3. IHPC variação homóloga - total (últimos 6 meses):")
    hicp = client.get_hicp(months=6)
    if "data" in hicp and hicp["data"]:
        for obs in hicp["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.2f}%")
    elif "error" in hicp:
        print(f"  Erro: {hicp['error']}")
    print()

    # 4. PIB trimestral (últimos 4 trimestres)
    print("4. PIB variação homóloga volume (últimos 4 trimestres):")
    gdp = client.get_gdp(quarters=4)
    if "data" in gdp and gdp["data"]:
        for obs in gdp["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.2f}%")
    elif "error" in gdp:
        print(f"  Erro: {gdp['error']}")
    print()

    # 5. Confiança indústria (últimos 6 meses)
    print("5. Confiança Indústria Transformadora (últimos 6 meses):")
    conf = client.get_confidence("manufacturing", months=6)
    if "data" in conf and conf["data"]:
        for obs in conf["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.1f}")
    elif "error" in conf:
        print(f"  Erro: {conf['error']}")
    print()

    # 6. Desemprego (últimos 4 trimestres)
    print("6. Taxa de desemprego (últimos 4 trimestres):")
    unemp = client.get_unemployment(quarters=4)
    if "data" in unemp and unemp["data"]:
        for obs in unemp["data"]:
            if obs["value"] is not None:
                print(f"  {obs['period']}: {obs['value']:.1f}%")
    elif "error" in unemp:
        print(f"  Erro: {unemp['error']}")
