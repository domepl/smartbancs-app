from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

INPUT_FILE = (
    BASE_DIR
    / "input"
    / "transactions_raw.csv"
)

OUTPUT_FILE = (
    BASE_DIR
    / "output"
    / "transactions_clean.csv"
)


def load_data():
    print("[ETL] Loading raw transactions...")

    dataframe = pd.read_csv(
        INPUT_FILE,
        dtype={
            "transaction_id": "string",
            "customer_id": "string",
            "currency": "string",
            "transaction_type": "string",
        },
    )

    print(
        f"[ETL] Records loaded: "
        f"{len(dataframe)}"
    )

    return dataframe


def clean_data(dataframe):
    df = dataframe.copy()

    initial_records = len(df)

    # Eliminar duplicados por transaction_id.
    df = df.drop_duplicates(
        subset=["transaction_id"],
        keep="first",
    )

    # Normalizar texto.
    df["currency"] = (
        df["currency"]
        .str.strip()
        .str.upper()
    )

    df["transaction_type"] = (
        df["transaction_type"]
        .str.strip()
        .str.upper()
    )

    df["customer_id"] = (
        df["customer_id"]
        .str.strip()
    )

    # Convertir amount a número.
    #
    # Valores inválidos como "abc"
    # pasan a NaN.
    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    )

    # Convertir diferentes formatos
    # de fecha.
    df["transaction_date"] = pd.to_datetime(
        df["transaction_date"],
        errors="coerce",
        format="mixed",
    )

    # Eliminar registros incompletos.
    df = df.dropna(
        subset=[
            "transaction_id",
            "customer_id",
            "amount",
            "currency",
            "transaction_date",
        ]
    )

    # Solo montos positivos.
    df = df[
        df["amount"] > 0
    ]

    # Normalizar fecha.
    df["transaction_date"] = (
        df["transaction_date"]
        .dt.strftime("%Y-%m-%d")
    )

    # Dos decimales.
    df["amount"] = (
        df["amount"]
        .round(2)
    )

    # Orden de columnas final.
    df = df[
        [
            "transaction_id",
            "customer_id",
            "transaction_type",
            "amount",
            "currency",
            "transaction_date",
        ]
    ]

    removed_records = (
        initial_records - len(df)
    )

    print(
        f"[ETL] Valid records: "
        f"{len(df)}"
    )

    print(
        f"[ETL] Removed records: "
        f"{removed_records}"
    )

    return df


def save_data(dataframe):
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print(
        f"[ETL] Output generated: "
        f"{OUTPUT_FILE}"
    )


def run_etl():
    print(
        "============================"
    )
    print(
        " SmartBancs ETL Process"
    )
    print(
        "============================"
    )

    dataframe = load_data()

    cleaned_dataframe = clean_data(
        dataframe
    )

    save_data(
        cleaned_dataframe
    )

    print(
        "[ETL] Average transaction amount: "
        f"{cleaned_dataframe['amount'].mean():.2f}"
    )

    print(
        "[ETL] Total processed amount: "
        f"{cleaned_dataframe['amount'].sum():.2f}"
    )

    print(
        "[ETL] Process completed successfully."
    )


if __name__ == "__main__":
    run_etl()