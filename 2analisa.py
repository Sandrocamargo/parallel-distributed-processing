import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Configurações visuais gerais
sns.set_theme(style="whitegrid")
plt.rcParams.update({"font.size": 11, "figure.autolayout": True})

OUTPUT_DIR = "images"


def calcular_ic_95(x):
    """Calcula a margem do Intervalo de Confiança de 95% usando distribuição t."""
    n = len(x)
    if n <= 1:
        return 0.0
    se = stats.sem(x)
    return se * stats.t.ppf((1 + 0.95) / 2.0, n - 1)


def analisar_e_gerar_graficos(caminho_csv, num_cores=None):
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(
            f"Arquivo de log '{caminho_csv}' não foi encontrado!"
        )

    if num_cores is None:
        try:
            import psutil

            num_cores = psutil.cpu_count(logical=False) or 4
        except ImportError:
            num_cores = os.cpu_count() or 4

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(caminho_csv)

    # Padronização e tolerância de nomenclatura de colunas
    if "quantidade_processadores" in df.columns:
        df.rename(
            columns={"quantidade_processadores": "quantidade_workers"},
            inplace=True,
        )

    # Se a coluna 'modo' não existir no CSV antigo, assume 'processos'
    if "modo" not in df.columns:
        df["modo"] = "processos"

    # 1. CÁLCULO DAS MÉTRICAS INDIVIDUAIS POR MODO
    # Define a base para Speedup (1 worker de cada modo)
    for modo in df["modo"].unique():
        sub_df = df[df["modo"] == modo]
        if 1 in sub_df["quantidade_workers"].values:
            tempo_base = sub_df[sub_df["quantidade_workers"] == 1][
                "tempo_execucao_segundos"
            ].mean()
        else:
            min_w = sub_df["quantidade_workers"].min()
            tempo_base = sub_df[sub_df["quantidade_workers"] == min_w][
                "tempo_execucao_segundos"
            ].mean()

        df.loc[df["modo"] == modo, "speedup"] = (
            tempo_base / df.loc[df["modo"] == modo, "tempo_execucao_segundos"]
        )
        df.loc[df["modo"] == modo, "eficiencia_%"] = (
            df.loc[df["modo"] == modo, "speedup"]
            / df.loc[df["modo"] == modo, "quantidade_workers"]
        ) * 100

    # 2. AGRUPAMENTO E ESTATÍSTICA (MODO x WORKERS)
    stats_df = (
        df.groupby(["modo", "quantidade_workers"])
        .agg(
            tempo_media=("tempo_execucao_segundos", "mean"),
            tempo_std=("tempo_execucao_segundos", "std"),
            tempo_ic=("tempo_execucao_segundos", calcular_ic_95),
            speedup_media=("speedup", "mean"),
            speedup_ic=("speedup", calcular_ic_95),
            eficiencia_media=("eficiencia_%", "mean"),
            eficiencia_ic=("eficiencia_%", calcular_ic_95),
        )
        .reset_index()
    )

    # Lei de Amdahl (Apenas para modo processos)
    p = stats_df["quantidade_workers"]
    s_amdahl = (1 / stats_df["speedup_media"] - 1 / p) / (1 - 1 / p)
    stats_df["fracao_sequencial_est_%"] = np.where(p > 1, s_amdahl * 100, 0)

    # 3. RELATÓRIO NO TERMINAL
    print("=" * 85)
    print("RELATÓRIO COMPARATIVO DE DESEMPENHO PARALELO: PROCESSOS VS THREADS")
    print(f"Cores de CPU Físicos Detectados: {num_cores}")
    print("=" * 85)

    for modo in stats_df["modo"].unique():
        print(f"\n>>> MODO DE EXECUÇÃO: {modo.upper()} <<<")
        cols = [
            "quantidade_workers",
            "tempo_media",
            "tempo_std",
            "speedup_media",
            "eficiencia_media",
        ]
        sub = stats_df[stats_df["modo"] == modo][cols]
        print(
            sub.to_string(
                index=False,
                formatters={
                    "tempo_media": "{:.2f}s".format,
                    "tempo_std": "{:.3f}".format,
                    "speedup_media": "{:.2f}x".format,
                    "eficiencia_media": "{:.1f}%".format,
                },
            )
        )

    # Palette de cores padronizada
    cores_modo = {"processos": "#1f77b4", "threads": "#d62728"}
    markers_modo = {"processos": "o", "threads": "s"}
    workers = sorted(stats_df["quantidade_workers"].unique())

    # --- Gráfico 1: Tempo Médio de Execução (Processos vs Threads) ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for modo in stats_df["modo"].unique():
        data = stats_df[stats_df["modo"] == modo]
        ax.errorbar(
            data["quantidade_workers"],
            data["tempo_media"],
            yerr=data["tempo_ic"],
            fmt=f"{markers_modo.get(modo, 'o')}-",
            color=cores_modo.get(modo, "black"),
            linewidth=2.2,
            capsize=4,
            label=f"Tempo Médio ({modo.capitalize()})",
        )
        ax.fill_between(
            data["quantidade_workers"],
            data["tempo_media"] - data["tempo_ic"],
            data["tempo_media"] + data["tempo_ic"],
            color=cores_modo.get(modo, "black"),
            alpha=0.12,
        )

    ax.axvline(
        x=num_cores,
        color="black",
        linestyle="--",
        alpha=0.7,
        label=f"Cores Físicos ({num_cores})",
    )
    ax.set_title(
        "Tempo de Execução: Processos vs Threads (IC 95%)",
        fontweight="bold",
    )
    ax.set_xlabel("Quantidade de Workers")
    ax.set_ylabel("Tempo de Execução (Segundos)")
    ax.set_xticks(workers)
    ax.legend(loc="upper right")
    plt.savefig(
        os.path.join(OUTPUT_DIR, "1_comparacao_tempo_execucao.png"), dpi=300
    )
    plt.close()

    # --- Gráfico 2: Speedup Real vs. Ideal ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    for modo in stats_df["modo"].unique():
        data = stats_df[stats_df["modo"] == modo]
        ax.errorbar(
            data["quantidade_workers"],
            data["speedup_media"],
            yerr=data["speedup_ic"],
            fmt=f"{markers_modo.get(modo, 'o')}-",
            color=cores_modo.get(modo, "black"),
            linewidth=2.2,
            capsize=4,
            label=f"Speedup ({modo.capitalize()})",
        )

    ax.plot(
        workers,
        workers,
        linestyle="--",
        color="gray",
        alpha=0.8,
        label="Speedup Ideal (Linear)",
    )
    ax.axvline(
        x=num_cores,
        color="black",
        linestyle="--",
        alpha=0.7,
        label=f"Cores Físicos ({num_cores})",
    )
    ax.set_title(
        "Curva Comparativa de Speedup (Impacto do GIL em CPU-Bound)",
        fontweight="bold",
    )
    ax.set_xlabel("Quantidade de Workers")
    ax.set_ylabel("Speedup (Vezes mais rápido)")
    ax.set_xticks(workers)
    ax.legend(loc="upper left")
    plt.savefig(os.path.join(OUTPUT_DIR, "2_comparacao_speedup.png"), dpi=300)
    plt.close()

    # --- Gráfico 3: Eficiência Agrupada ---
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.barplot(
        data=df,
        x="quantidade_workers",
        y="eficiencia_%",
        hue="modo",
        ax=ax,
        palette=cores_modo,
        errorbar=("ci", 95),
        capsize=0.1,
    )
    ax.axhline(
        100,
        linestyle="--",
        color="gray",
        alpha=0.7,
        label="Eficiência Ideal (100%)",
    )
    ax.set_title(
        "Eficiência de Paralelização: Processos vs Threads",
        fontweight="bold",
    )
    ax.set_xlabel("Quantidade de Workers")
    ax.set_ylabel("Eficiência (%)")
    ax.legend(title="Modo")
    plt.savefig(
        os.path.join(OUTPUT_DIR, "3_comparacao_eficiencia.png"), dpi=300
    )
    plt.close()

    # --- Gráfico 4: Boxplot do Comportamento das Amostras (Dispersão) ---
    fig, ax = plt.subplots(figsize=(10, 5.5))
    sns.boxplot(
        data=df,
        x="quantidade_workers",
        y="tempo_execucao_segundos",
        hue="modo",
        ax=ax,
        palette=cores_modo,
        boxprops=dict(alpha=0.7),
    )
    ax.set_title(
        "Distribuição e Variabilidade do Tempo por Modo",
        fontweight="bold",
    )
    ax.set_xlabel("Quantidade de Workers")
    ax.set_ylabel("Tempo de Execução (Segundos)")
    ax.legend(title="Modo")
    plt.savefig(
        os.path.join(OUTPUT_DIR, "4_variabilidade_boxplot.png"), dpi=300
    )
    plt.close()

    print(
        f"\nSucesso! Gráficos comparativos gerados na pasta: '{OUTPUT_DIR}/'\n"
    )


if __name__ == "__main__":
    analisar_e_gerar_graficos("./benchmark_paralelismo.csv")
