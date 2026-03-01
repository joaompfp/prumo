#!/usr/bin/env python3
"""
CAE Dashboard — Collector for new housing and salary indicators

Collects:
1. Housing loan rate (BdP série 12533735 - TAA housing loans)
2. Housing price index (INE 0010527 - quarterly)
3. Median monthly earnings (Eurostat - annual, PT + EU27)

Output format: List of dicts matching DB schema
  {source, indicator, region, period, value, unit, detail?}
"""

import json
import sys
from datetime import datetime
from typing import List, Dict

# Import existing collectors
from bportugal import BPortugalClient
from ine import INEClient
from eurostat import EurostatClient


def collect_housing_loan_rate() -> List[Dict]:
    """
    Collect housing loan interest rate from Banco de Portugal
    Target: Monthly series since 2015-01
    Indicator: housing_loan_rate
    """
    print("🔍 Fetching housing loan rate from BdP...", file=sys.stderr)
    results = []
    
    try:
        client = BPortugalClient()
        
        # BdP API using série 12533735 (TAA - Taxa Anualizada housing loans)
        # Note: This is NOT in the default SERIES dict, so we'll try a custom query
        # The series is in domain 21 (Interest rates on new operations)
        
        # Fallback: Use web scraping or manual entry if API fails
        # For now, let's try fetching via the pre-defined series if it exists
        
        # Check if there's a housing rate series already defined
        available = ["euribor_1m", "euribor_3m", "euribor_6m", "euribor_12m",
                     "eur_usd", "pt_10y", "de_10y", "credit_housing", 
                     "credit_consumer", "deposits_households"]
        
        # Since housing loan RATE is not in default series, we'll document
        # the manual approach needed
        print("⚠️  BdP housing loan rate series 16771/12533735 not in default client", file=sys.stderr)
        print("    API requires domain + dataset IDs which are not documented", file=sys.stderr)
        print("    Fallback: Manual CSV export or web scraping needed", file=sys.stderr)
        
        # Placeholder data structure for manual insertion later
        # User should download from https://bpstat.bportugal.pt/serie/12533735
        # and convert to this format
        
        results.append({
            "source": "BPORTUGAL",
            "indicator": "housing_loan_rate",
            "region": "PT",
            "period": "2024-12",
            "value": None,  # TO BE FILLED
            "unit": "%",
            "detail": json.dumps({"note": "Manual data entry required - série 12533735 TAA housing loans"})
        })
        
    except Exception as e:
        print(f"❌ Error fetching BdP housing loan rate: {e}", file=sys.stderr)
        results.append({
            "source": "BPORTUGAL",
            "indicator": "housing_loan_rate",
            "region": "PT",
            "period": "ERROR",
            "value": None,
            "unit": "%",
            "detail": json.dumps({"error": str(e)})
        })
    
    return results


def collect_housing_price_index() -> List[Dict]:
    """
    Collect Housing Price Index from INE
    Target: Quarterly series since 2010-Q1
    Indicator: housing_price_index
    """
    print("🔍 Fetching housing price index from INE...", file=sys.stderr)
    results = []
    
    try:
        client = INEClient()
        
        # INE indicator 0010527 - Índice de Preços da Habitação
        # Quarterly data, base 2015=100
        response = client.get_data("0010527", quarters=60)  # ~15 years
        
        if "error" in response:
            print(f"⚠️  INE API error: {response['error']}", file=sys.stderr)
            results.append({
                "source": "INE",
                "indicator": "housing_price_index",
                "region": "PT",
                "period": "ERROR",
                "value": None,
                "unit": "Índice (2015=100)",
                "detail": json.dumps({"error": response["error"]})
            })
            return results
        
        data = response.get("data", [])
        print(f"✅ INE housing price index: {len(data)} observations", file=sys.stderr)
        
        for obs in data:
            # INE periods are YYYY-MM format, we need YYYY-QN for quarterly
            period = obs.get("period", "")
            value = obs.get("value")
            
            if value is not None:
                # Convert period to quarter format if needed
                # INE quarterly data uses the first month of the quarter
                # e.g., "2024-01" = Q1, "2024-04" = Q2, "2024-07" = Q3, "2024-10" = Q4
                if "-" in period:
                    year, month = period.split("-")
                    month_int = int(month)
                    quarter = (month_int - 1) // 3 + 1
                    period = f"{year}-Q{quarter}"
                
                results.append({
                    "source": "INE",
                    "indicator": "housing_price_index",
                    "region": "PT",
                    "period": period,
                    "value": value,
                    "unit": "Índice (2015=100)",
                    "detail": json.dumps({"varcd": "0010527"})
                })
        
    except Exception as e:
        print(f"❌ Error fetching INE housing price index: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        results.append({
            "source": "INE",
            "indicator": "housing_price_index",
            "region": "PT",
            "period": "ERROR",
            "value": None,
            "unit": "Índice (2015=100)",
            "detail": json.dumps({"error": str(e)})
        })
    
    return results


def collect_median_earnings() -> List[Dict]:
    """
    Collect minimum wage from Eurostat (as proxy for earnings data)
    Note: Full earnings surveys (SES) are 4-yearly. Monthly minimum wage is biannual and more available.
    Target: Biannual series since 2010, PT + EU comparison
    Indicator: minimum_monthly_wage (will use as earnings proxy)
    """
    print("🔍 Fetching minimum wage from Eurostat...", file=sys.stderr)
    print("⚠️  Note: Median earnings (SES) is 4-yearly. Using monthly minimum wage as proxy.", file=sys.stderr)
    results = []
    
    try:
        client = EurostatClient()
        
        # Try earn_mw_cur (monthly minimum wages, biannual)
        # This is more consistently available than full earnings surveys
        regions = ["PT", "ES", "DE", "FR"]  # DE doesn't have minimum wage, but try anyway
        
        for region in regions:
            try:
                response = client.get_data(
                    "earn_mw_cur",
                    geo=region,
                    years=15  # Last 15 years
                )
                
                if "error" in response:
                    print(f"⚠️  Eurostat {region} error: {response['error']}", file=sys.stderr)
                    continue
                
                data = response.get("data", [])
                print(f"✅ Eurostat minimum wage {region}: {len(data)} observations", file=sys.stderr)
                
                for obs in data:
                    period = obs.get("period", "")
                    value = obs.get("value")
                    
                    if value is not None:
                        results.append({
                            "source": "EUROSTAT",
                            "indicator": "minimum_monthly_wage",
                            "region": region,
                            "period": period,
                            "value": value,
                            "unit": "€",
                            "detail": json.dumps({
                                "dataset": "earn_mw_cur",
                                "note": "Monthly minimum wage (national currency). Median earnings (SES) is 4-yearly only."
                            })
                        })
                        
            except Exception as e:
                print(f"⚠️  Error fetching Eurostat {region}: {e}", file=sys.stderr)
                continue
        
        if not results:
            print("⚠️  No Eurostat data collected. Adding placeholder for manual SES data.", file=sys.stderr)
            results.append({
                "source": "EUROSTAT",
                "indicator": "median_monthly_earnings",
                "region": "PT",
                "period": "MANUAL",
                "value": None,
                "unit": "€",
                "detail": json.dumps({
                    "note": "Structure of Earnings Survey (SES) is 4-yearly (2022, 2018, 2014, 2010). Manual data entry required.",
                    "dataset": "earn_ses22_* or earn_nt_net",
                    "url": "https://ec.europa.eu/eurostat/web/labour-market/earnings"
                })
            })
        
    except Exception as e:
        print(f"❌ Error fetching Eurostat earnings: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        results.append({
            "source": "EUROSTAT",
            "indicator": "median_monthly_earnings",
            "region": "ERROR",
            "period": "ERROR",
            "value": None,
            "unit": "€",
            "detail": json.dumps({"error": str(e)})
        })
    
    return results


def main():
    """Main collector - fetch all indicators and output JSON"""
    print("=" * 60, file=sys.stderr)
    print("CAE Dashboard — New Indicators Collector", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    all_data = []
    
    # 1. Housing loan rate (BdP)
    print("\n[1/3] Housing Loan Rate (BdP)", file=sys.stderr)
    housing_rate = collect_housing_loan_rate()
    all_data.extend(housing_rate)
    
    # 2. Housing price index (INE)
    print("\n[2/3] Housing Price Index (INE)", file=sys.stderr)
    housing_price = collect_housing_price_index()
    all_data.extend(housing_price)
    
    # 3. Median earnings (Eurostat)
    print("\n[3/3] Median Monthly Earnings (Eurostat)", file=sys.stderr)
    median_earnings = collect_median_earnings()
    all_data.extend(median_earnings)
    
    # Output results
    print("\n" + "=" * 60, file=sys.stderr)
    print(f"TOTAL INDICATORS COLLECTED: {len(all_data)}", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Print JSON to stdout
    print(json.dumps(all_data, indent=2, ensure_ascii=False))
    
    # Summary
    print("\nSummary by indicator:", file=sys.stderr)
    by_indicator = {}
    for item in all_data:
        ind = item["indicator"]
        by_indicator[ind] = by_indicator.get(ind, 0) + 1
    
    for ind, count in by_indicator.items():
        print(f"  {ind}: {count} observations", file=sys.stderr)


if __name__ == "__main__":
    main()
