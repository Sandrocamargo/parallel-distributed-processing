import concurrent.futures
import configparser
import csv
import math
import multiprocessing
import os
import time


def load_config(config_path):
    """Lê e valida os parâmetros do arquivo de configuração."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"O arquivo de configuração '{config_path}' não foi encontrado!"
        )

    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")

    return {
        "COMPLEXITY": config.getint("EXPERIMENT", "complexity", fallback=16_000_000),
        "REPETITIONS": config.getint("EXPERIMENT", "repetitions", fallback=10),
        "MAX_WORKERS": config.getint("EXPERIMENT", "max_workers", fallback=20),
        "LOG_FILENAME": config.get(
            "EXPERIMENT", "log_filename", fallback="benchmark_paralelismo.csv"
        ),
    }


def heavy_task(n):
    """Tarefa CPU-bound que simula processamento pesado sem usar sleep()."""
    total = 0.0
    for i in range(1, n + 1):
        total += math.sqrt(i) * math.sin(i)
    return total


def run_chunk(args):
    """Função auxiliar para cada worker processar sua fatia."""
    (sub_n,) = args
    return heavy_task(sub_n)


# ==============================================================================
# ESTRATEGIAS DE EXECUÇÃO
# ==============================================================================


def run_processos(tasks, num_workers):
    """Paralelismo via múltiplos processos (multiprocessing.Pool)."""
    with multiprocessing.Pool(processes=num_workers) as pool:
        pool.map(run_chunk, tasks)


def run_threads_gil(tasks, num_workers):
    """Paralelismo via threads sujeitas ao GIL (ThreadPoolExecutor)."""
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=num_workers
    ) as executor:
        list(executor.map(run_chunk, tasks))


def run_threads_poolexecutor(tasks, num_workers):
    """Paralelismo via múltiplos processos (ProcessPoolExecutor)."""
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=num_workers
    ) as executor:
        list(executor.map(run_chunk, tasks))


# Mapeamento dos modos de execução para suas respectivas funções
EXECUTION_STRATEGIES = {
    "processos": run_processos,
    "threads(GIL)": run_threads_gil,
    "threads(poolexecutor)": run_threads_poolexecutor,
}


# ==============================================================================
# FUNÇÃO PRINCIPAL DE EXECUÇÃO
# ==============================================================================


def execute_benchmark(mode, num_workers, complexity):
    """Divide a carga total entre os workers e despacha para a função correspondente."""
    start_time = time.perf_counter()

    if num_workers == 1:
        # Execução sequencial direta em 1 worker
        heavy_task(complexity)
    else:
        chunk_size = complexity // num_workers
        tasks = [(chunk_size,) for _ in range(num_workers)]

        # Seleciona e executa a função do modo correspondente
        strategy = EXECUTION_STRATEGIES.get(mode)
        if not strategy:
            raise ValueError(f"Modo de execução desconhecido: '{mode}'")

        strategy(tasks, num_workers)

    end_time = time.perf_counter()
    return end_time - start_time


# ==============================================================================
# PONTO DE ENTRADA DO SCRIPT
# ==============================================================================

if __name__ == "__main__":
    multiprocessing.freeze_support()

    params = load_config("0params.cfg")

    COMPLEXITY = params["COMPLEXITY"]
    REPETITIONS = params["REPETITIONS"]
    MAX_WORKERS = params["MAX_WORKERS"]
    LOG_FILENAME = params["LOG_FILENAME"]

    MODES = list(EXECUTION_STRATEGIES.keys())

    print("=" * 65)
    print("INICIANDO BENCHMARK COMPARATIVO DE PARALELISMO")
    print("Parâmetros lidos de: 0params.cfg")
    print(f"Complexidade: {COMPLEXITY:_} iterações | Repetições: {REPETITIONS}")
    print(f"Workers avaliados: 1 até {MAX_WORKERS}")
    print("=" * 65)

    with open(LOG_FILENAME, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["modo", "repeticao", "quantidade_workers", "tempo_execucao_segundos"]
        )

        for mode in MODES:
            print("\n" + "#" * 50)
            print(f"=== EXECUÇÃO VIA: {mode.upper()} ===")
            print("#" * 50)

            for num_workers in range(1, MAX_WORKERS + 1):
                print(f"\n[Modo: {mode} | Avaliando {num_workers} Worker(s)...]")

                for rep in range(1, REPETITIONS + 1):
                    elapsed_time = execute_benchmark(mode, num_workers, COMPLEXITY)

                    writer.writerow(
                        [mode, rep, num_workers, f"{elapsed_time:.4f}"]
                    )
                    csv_file.flush()

                    print(
                        f" -> Modo: {mode:<22} | Repetição {rep:2d}/{REPETITIONS} | "
                        f"Workers: {num_workers:2d} | Tempo: {elapsed_time:.2f}s"
                    )

    print("\n" + "=" * 65)
    print(f"Benchmark finalizado com sucesso! Log salvo em: {LOG_FILENAME}")
    print("=" * 65)
