# Abre o arquivo benchmark_paralelismo.csv, gera os gráficos de análise e armazena na pasta images.
# Após a execução deste script, analise o conteúdo da pasta images

import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Configurações visuais dos gráficos
sns.set_theme(style="whitegrid")
plt.rcParams.update({"font.size": 11, "figure.autolayout": True})

OUTPUT_DIR = "images"


def analisar_e_gerar_graficos(caminho_csv, num_cores=None):
    if not os.path.exists(caminho_csv):
        raise FileNotFoundError(f"Arquivo de log '{caminho_csv}' não encontrado!")

    if num_cores is None:
        try:
            import psutil
            num_cores = psutil.cpu_count(logical=False) or 4
        except ImportError:
            num_cores = os.cpu_count() or 4
            
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = pd.read_csv(caminho_csv)

    # 1. EXIBIÇÃO DOS DADOS BRUTOS NA TELA
    print("=" * 80)
    print("EXIBIÇÃO DOS DADOS BRUTOS (LOG MEDIDO):")
    print(f"Cores de CPU configuradas/detectadas: {num_cores}")
    print("=" * 80)
    print(f"{'Repetição':<12} | {'Processadores (Workers)':<25} | {'Tempo (s)':<15}")
    print("-" * 80)

    for idx, row in df.iterrows():
        print(f"{int(row['repeticao']):<12d} | {int(row['quantidade_processadores']):<25d} | {float(row['tempo_execucao_segundos']):<15.4f}")

    # 2. CÁLCULO DAS MÉTRICAS A NÍVEL DE OBSERVAÇÃO INDIVIDUAL
    # Média base (1 worker) para cálculo de speedup
    if 1 in df["quantidade_processadores"].values:
        tempo_base = df[df["quantidade_processadores"] == 1]["tempo_execucao_segundos"].mean()
    else:
        min_workers = df["quantidade_processadores"].min()
        tempo_base = df[df["quantidade_processadores"] == min_workers]["tempo_execucao_segundos"].mean()
        print(f"\n[AVISO] Teste com 1 processador não encontrado. Usando {min_workers} worker(s) como base.\n")

    # Adiciona Speedup e Eficiência por linha/repetição no DataFrame bruto
    df["speedup"] = tempo_base / df["tempo_execucao_segundos"]
    df["eficiencia_%"] = (df["speedup"] / df["quantidade_processadores"]) * 100

    # 3. AGRUPAMENTO E CÁLCULO DOS INTERVALOS DE CONFIANÇA (IC 95%)
    def calcular_ic_95(x):
        n = len(x)
        if n <= 1:
            return 0.0
        se = stats.sem(x)
        return se * stats.t.ppf((1 + 0.95) / 2.0, n - 1)

    stats_df = (
        df.groupby("quantidade_processadores")
        .agg(
            tempo_media=("tempo_execucao_segundos", "mean"),
            tempo_std=("tempo_execucao_segundos", "std"),
            tempo_ic=("tempo_execucao_segundos", calcular_ic_95),
            tempo_min=("tempo_execucao_segundos", "min"),
            tempo_max=("tempo_execucao_segundos", "max"),
            speedup_media=("speedup", "mean"),
            speedup_ic=("speedup", calcular_ic_95),
            eficiencia_media=("eficiencia_%", "mean"),
            eficiencia_ic=("eficiencia_%", calcular_ic_95),
        )
        .reset_index()
    )

    stats_df["ic_95_min"] = stats_df["tempo_media"] - stats_df["tempo_ic"]
    stats_df["ic_95_max"] = stats_df["tempo_media"] + stats_df["tempo_ic"]

    p = stats_df["quantidade_processadores"]
    s_amdahl = (1 / stats_df["speedup_media"] - 1 / p) / (1 - 1 / p)
    stats_df["fracao_sequencial_est_%"] = np.where(p > 1, s_amdahl * 100, 0)

    # 4. IMPRESSÃO DO RELATÓRIO ESTATÍSTICO NO TERMINAL
    print("\n" + "=" * 80)
    print("RELATÓRIO DE ANÁLISE ESTATÍSTICA DE DESEMPENHO PARALELO")
    print("=" * 80)

    print("\n[1] METRICAS DE ESCALABILIDADE (SPEEDUP E EFICIÊNCIA):")
    cols_hpc = ["quantidade_processadores", "tempo_media", "tempo_std", "speedup_media", "eficiencia_media"]
    print(
        stats_df[cols_hpc].to_string(
            index=False,
            formatters={
                "tempo_media": "{:.2f}s".format,
                "tempo_std": "{:.3f}".format,
                "speedup_media": "{:.2f}x".format,
                "eficiencia_media": "{:.1f}%".format,
            },
        )
    )

    print("\n[2] VARIABILIDADE E INTERVALOS DE CONFIANÇA (95%):")
    cols_var = ["quantidade_processadores", "tempo_min", "tempo_max", "ic_95_min", "ic_95_max"]
    print(
        stats_df[cols_var].to_string(
            index=False,
            formatters={
                "tempo_min": "{:.2f}s".format,
                "tempo_max": "{:.2f}s".format,
                "ic_95_min": "{:.2f}s".format,
                "ic_95_max": "{:.2f}s".format,
            },
        )
    )

    print("\n[3] OVERHEAD E FRAÇÃO SEQUENCIAL ESTIMADA (LEI DE AMDAHL):")
    cols_amdahl = ["quantidade_processadores", "speedup_media", "fracao_sequencial_est_%"]
    print(
        stats_df[cols_amdahl].to_string(
            index=False,
            formatters={
                "speedup_media": "{:.2f}x".format,
                "fracao_sequencial_est_%": "{:.2f}%".format,
            },
        )
    )
    print("\n" + "=" * 80)

    # 5. GERAÇÃO DOS GRÁFICOS COM INTERVALO DE CONFIANÇA
    workers = stats_df["quantidade_processadores"].values

    # --- Gráfico 1: Tempo Médio de Execução com IC ---
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        workers,
        stats_df["tempo_media"],
        yerr=stats_df["tempo_ic"],
        fmt="o-",
        color="#1f77b4",
        linewidth=2.5,
        capsize=5,
        capthick=1.5,
        label="Tempo Médio Medido (IC 95%)",
    )
    ax.fill_between(
        workers,
        stats_df["tempo_media"] - stats_df["tempo_ic"],
        stats_df["tempo_media"] + stats_df["tempo_ic"],
        color="#1f77b4",
        alpha=0.15,
    )
    ax.axvline(
        x=num_cores,
        color="red",
        linestyle="--",
        alpha=0.7,
        label=f"Limite Físico ({num_cores} Cores)",
    )
    ax.set_title("Tempo de Execução Médio vs. Processadores (IC 95%)", fontweight="bold")
    ax.set_xlabel("Quantidade de Processadores / Threads (Workers)")
    ax.set_ylabel("Tempo de Execução (Segundos)")
    ax.set_xticks(workers)
    ax.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "1_tempo_execucao.png"), dpi=300)
    plt.close()

    # --- Gráfico 2: Speedup Real com IC vs. Ideal ---
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.errorbar(
        workers,
        stats_df["speedup_media"],
        yerr=stats_df["speedup_ic"],
        fmt="o-",
        color="#2ca02c",
        linewidth=2.5,
        capsize=5,
        capthick=1.5,
        label="Speedup Real (IC 95%)",
    )
    ax.fill_between(
        workers,
        stats_df["speedup_media"] - stats_df["speedup_ic"],
        stats_df["speedup_media"] + stats_df["speedup_ic"],
        color="#2ca02c",
        alpha=0.15,
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
        color="red",
        linestyle="--",
        alpha=0.7,
        label=f"Limite Físico ({num_cores} Cores)",
    )
    ax.set_title("Curva de Speedup com Intervalo de Confiança (95%)", fontweight="bold")
    ax.set_xlabel("Quantidade de Processadores / Threads (Workers)")
    ax.set_ylabel("Speedup (Vezes mais rápido)")
    ax.set_xticks(workers)
    ax.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "2_speedup.png"), dpi=300)
    plt.close()

    # --- Gráfico 3: Eficiência com Barras de Erro (IC 95%) ---
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(
        workers,
        stats_df["eficiencia_media"],
        yerr=stats_df["eficiencia_ic"],
        capsize=5,
        color="#ff7f0e",
        edgecolor="black",
        alpha=0.85,
        error_kw={"ecolor": "black", "lw": 1.5, "capthick": 1.5},
        label="Eficiência Média (IC 95%)",
    )
    ax.axhline(100, linestyle="--", color="gray", alpha=0.7, label="Eficiência Ideal (100%)")
    ax.axvline(
        x=num_cores + 0.5,
        color="red",
        linestyle="--",
        alpha=0.7,
        label="Início do Hyper-Threading",
    )

    for bar, ic in zip(bars, stats_df["eficiencia_ic"]):
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + ic + 2.0,  # Posiciona o texto acima da barra de erro
            f"{yval:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_title("Eficiência de Paralelização por Processador (IC 95%)", fontweight="bold")
    ax.set_xlabel("Quantidade de Processadores / Threads (Workers)")
    ax.set_ylabel("Eficiência (%)")
    ax.set_ylim(0, max(stats_df["eficiencia_media"] + stats_df["eficiencia_ic"]) + 15)
    ax.set_xticks(workers)
    ax.legend()
    plt.savefig(os.path.join(OUTPUT_DIR, "3_eficiencia.png"), dpi=300)
    plt.close()

    # --- Gráfico 4: Boxplot com Sobreposição de Pontos (Stripplot) ---
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(
        data=df,
        x="quantidade_processadores",
        y="tempo_execucao_segundos",
        ax=ax,
        boxprops=dict(alpha=0.6),
    )
    # Adiciona os pontos individuais para ver visualmente a dispersão real
    sns.stripplot(
        data=df,
        x="quantidade_processadores",
        y="tempo_execucao_segundos",
        color="black",
        alpha=0.5,
        jitter=0.2,
        ax=ax,
    )
    ax.set_title("Variabilidade e Distribuição das Amostras Médias", fontweight="bold")
    ax.set_xlabel("Quantidade de Processadores / Threads (Workers)")
    ax.set_ylabel("Tempo de Execução (Segundos)")
    plt.savefig(os.path.join(OUTPUT_DIR, "4_variabilidade_boxplot.png"), dpi=300)
    plt.close()

    print(f"Sucesso! Gráficos atualizados e salvos na pasta: '{OUTPUT_DIR}/'\n")


if __name__ == "__main__":
    analisar_e_gerar_graficos("./benchmark_paralelismo.csv")
