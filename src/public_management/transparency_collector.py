"""Portal da Transparencia collection and enrichment utilities.

This module integrates the former ``malha-transparencia`` workflow into the
public-management pipeline. It collects contracts by supplier CNPJ, flattens the
nested API payload, and leaves the resulting CSV ready for network conversion.
"""

from __future__ import annotations

import ast
import json
import re
import time
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd
import requests


PORTAL_CONTRACTS_URL = "https://api.portaldatransparencia.gov.br/api-de-dados/contratos/cpf-cnpj"

DEFAULT_INVESTIGATION_CNPJS = [
    "19.821.234/0001-28",
    "15.102.288/0001-82",
    "33.950.222/0001-24",
    "17.262.197/0001-30",
    "17.262.213/0007-80",
    "14.310.577/0001-04",
    "06.324.922/0003-00",
    "61.522.512/0001-02",
    "11.178.032/0001-06",
    "28.660.349/0005-00",
    "33.412.792/0001-60",
    "44.023.661/0001-08",
    "00.103.582/0095-11",
    "03.251.409/0001-79",
    "07.248.576/0001-11",
    "07.248.576/0010-02",
    "15.563.826/0001-36",
    "19.331.200/0001-55",
    "19.305.688/0001-46",
    "17.162.082/0031-99",
    "09.253.464/0001-84",
    "04.858.041/0001-74",
    "01.340.937/0001-79",
    "01.340.937/0018-17",
    "01.340.937/0024-65",
    "02.154.943/0001-02",
    "02.154.943/0020-67",
    "61.095.923/0001-69",
    "61.095.923/0006-73",
    "61.095.923/0046-60",
    "34.152.199/0001-95",
    "34.152.199/0011-67",
    "61.575.775/0001-80",
    "61.575.775/0026-38",
    "61.575.775/0106-57",
    "40.450.769/0001-26",
    "40.450.769/0119-18",
    "40.450.769/0104-31",
    "61.226.890/0001-49",
    "04.979.406/0001-19",
    "05.606.437/0001-97",
    "33.000.167/081942",
    "58.580.465/0028-69",
    "58.580.465/0045-60",
    "31.876.709/0001-89",
    "04.743.858/0001-05",
    "11.245.802/0001-88",
    "27.429.099/0001-06",
    "33.317.249/0001-84",
    "61.584.223/0001-38",
    "61.584.223/0026-96",
    "61.584.223/0018-86",
    "07.022.301/0001-65",
    "05.314.015/0001-48",
    "17.186.461/0001-01",
    "17.186.461/0002-84",
    "17.186.461/0073-78",
    "17.186.461/0084-20",
    "33.000.167/0001-01",
    "33.000.167/0002-92",
    "33.000.167/0015-07",
    "34.274.233/0001-02",
    "02.709.449/0001-59",
    "42.540.211/0001-67",
    "00.000.000/0001-91",
    "33.000.167/0125-41",
    "10.693.579/0001-79",
    "09.455.260/0001-26",
    "33.000.167/1111-08",
    "33.000.167/0143-23",
    "33.000.167/0809-70",
    "10.806.670/0001-53",
    "53.371.667/0001-67",
    "03.813.899/0001-50",
    "61.270.223/0001-63",
    "48.619.426/0001-54",
    "11.457.216/0001-05",
    "58.092.297/0001-42",
    "57.541.377/0001-75",
]


def format_cnpj(cnpj: str) -> str:
    """Return only numeric characters from a CNPJ string."""
    return re.sub(r"[^0-9]", "", str(cnpj or ""))


def parse_cnpj_text(text: str) -> list[str]:
    """Parse CNPJs from comma, semicolon, whitespace, or line-separated text."""
    candidates = re.split(r"[\s,;]+", text.strip())
    return [cnpj for cnpj in (format_cnpj(item) for item in candidates) if cnpj]


def _notify(callback: Callable[[str], None] | None, message: str) -> None:
    """Send a progress message when a callback is available."""
    if callback:
        callback(message)


def fetch_contracts_for_cnpj(
    cnpj: str,
    api_key: str,
    *,
    request_delay: float = 0.5,
    timeout: int = 60,
    max_pages: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> list[dict]:
    """Fetch all contract pages for one CNPJ from the Portal da Transparencia."""
    clean_cnpj = format_cnpj(cnpj)
    if not clean_cnpj:
        return []

    headers = {
        "Accept": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "chave-api-dados": api_key,
    }
    page = 1
    contracts: list[dict] = []

    while True:
        if max_pages is not None and page > max_pages:
            break

        params = {"cpfCnpj": clean_cnpj, "pagina": page}
        response = requests.get(PORTAL_CONTRACTS_URL, headers=headers, params=params, timeout=timeout)

        content_type = response.headers.get("content-type", "")
        if response.status_code != 200:
            if "text/html" in content_type or "<html" in response.text[:200].lower():
                raise RuntimeError(
                    "O Portal da Transparencia devolveu uma pagina HTML em vez de JSON. "
                    "Isso normalmente indica bloqueio/validacao humana, chave de API invalida "
                    "ou alteracao temporaria do servico. Tente novamente em alguns minutos e "
                    "confira se a chave da API foi copiada corretamente."
                )
            raise RuntimeError(
                f"Portal da Transparencia returned {response.status_code} for CNPJ {clean_cnpj}, "
                f"page {page}: {response.text[:300]}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "O Portal da Transparencia respondeu sem JSON valido. "
                f"Content-Type recebido: {content_type or 'desconhecido'}."
            ) from exc
        if not payload:
            break

        contracts.extend(payload)
        _notify(progress_callback, f"CNPJ {clean_cnpj}: pagina {page} com {len(payload)} contratos.")
        page += 1
        time.sleep(request_delay)

    return contracts


def collect_contracts(
    cnpjs: Iterable[str],
    api_key: str,
    *,
    request_delay: float = 0.5,
    timeout: int = 60,
    max_pages_per_cnpj: int | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> pd.DataFrame:
    """Collect contracts for several CNPJs and return a deduplicated DataFrame."""
    if not api_key.strip():
        raise ValueError("A chave da API do Portal da Transparencia e obrigatoria.")

    all_contracts: list[dict] = []
    clean_cnpjs = [format_cnpj(cnpj) for cnpj in cnpjs if format_cnpj(cnpj)]

    for index, cnpj in enumerate(clean_cnpjs, start=1):
        _notify(progress_callback, f"Coletando CNPJ {index}/{len(clean_cnpjs)}: {cnpj}.")
        all_contracts.extend(
            fetch_contracts_for_cnpj(
                cnpj,
                api_key,
                request_delay=request_delay,
                timeout=timeout,
                max_pages=max_pages_per_cnpj,
                progress_callback=progress_callback,
            )
        )

    if not all_contracts:
        return pd.DataFrame()

    df = pd.DataFrame(all_contracts)
    if "id" in df.columns:
        df = df.drop_duplicates(subset=["id"])
    else:
        df = df.drop_duplicates()
    return df.reset_index(drop=True)


def _coerce_nested_value(value):
    """Convert nested strings returned in CSVs back to dict/list objects."""
    if isinstance(value, (dict, list)):
        return value
    if pd.isna(value):
        return None
    if not isinstance(value, str):
        return None

    for loader in (json.loads, ast.literal_eval):
        try:
            return loader(value)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            continue
    return None


def enrich_contracts_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten nested Portal da Transparencia columns into analysis columns."""
    if df.empty:
        return df.copy()

    nested_columns = {
        "fornecedor": "fornecedor_",
        "unidadeGestora": "unidadeGestora_",
        "unidadeGestoraCompras": "unidadeGestoraCompras_",
        "compra": "compra_",
    }

    base_df = df.copy()
    frames = [base_df]

    for column_name, prefix in nested_columns.items():
        if column_name not in base_df.columns:
            continue

        parsed = base_df[column_name].apply(_coerce_nested_value)
        normalized = pd.json_normalize(parsed).add_prefix(prefix)
        normalized.index = base_df.index
        frames.append(normalized)

    enriched = pd.concat(frames, axis=1)
    enriched = enriched.drop(columns=[col for col in nested_columns if col in enriched.columns])
    return enriched


def save_contract_pipeline_outputs(
    raw_df: pd.DataFrame,
    output_dir: str | Path,
    *,
    raw_filename: str = "contratos_consolidados.csv",
    enriched_filename: str = "contratos_enriquecidos.csv",
) -> tuple[Path, Path, pd.DataFrame]:
    """Save raw and enriched contracts and return their paths plus the enriched frame."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    raw_path = output_path / raw_filename
    enriched_path = output_path / enriched_filename
    enriched_df = enrich_contracts_dataframe(raw_df)

    raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
    enriched_df.to_csv(enriched_path, index=False, encoding="utf-8-sig")

    return raw_path, enriched_path, enriched_df
