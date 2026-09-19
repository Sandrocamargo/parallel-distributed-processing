import configparser
import csv
import math
import multiprocessing
import os
import time


def load_config(config_path="params.cfg"):
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
    """
    Tarefa CPU-bound que simula um processamento pesado sem usar sleep().
    Recebe o parâmetro de complexidade e executa operações matemáticas.
    """
    total = 0.0
    for i in range(1, n + 1):
        total += math.sqrt(i) * math.sin(i)
    return total


def run_chunk(args):
    """Função auxiliar para cada worker processar sua fatia."""
    (sub_n,) = args
    return heavy_task(sub_n)


def execute_parallel(num_workers, complexity):
    """Divide a carga total entre os workers e mede o tempo do bloco."""
    # Divisão da carga de trabalho entre os workers disponíveis
    chunk_size = complexity // num_workers
    tasks = [(chunk_size,) for _ in range(num_workers)]

    start_time = time.perf_counter()

    if num_workers == 1:
        # Execução Sequencial Direta (1 worker)
        heavy_task(complexity)
    else:
        # Execução Paralela dividida entre múltiplos processos
        with multiprocessing.Pool(processes=num_workers) as pool:
            pool.map(run_chunk, tasks)

    end_time = time.perf_counter()
    return end_time - start_time


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Carrega os parâmetros a partir do arquivo params.cfg
    params = load_config("params.cfg")

    COMPLEXITY = params["COMPLEXITY"]
    REPETITIONS = params["REPETITIONS"]
    MAX_WORKERS = params["MAX_WORKERS"]
    LOG_FILENAME = params["LOG_FILENAME"]

    print("=" * 60)
    print("INICIANDO BENCHMARK DE PROCESSAMENTO PARALELO")
    print(f"Parâmetros lidos de: params.cfg")
    print(f"Complexidade: {COMPLEXITY} iteracoes | Repeticoes: {REPETITIONS}")
    print(f"Processadores/Threads avaliados: 1 ate {MAX_WORKERS}")
    print("=" * 60)

    # Inicializa o arquivo de Log CSV
    with open(LOG_FILENAME, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["repeticao", "quantidade_processadores", "tempo_execucao_segundos"]
        )

        # Loop de 1 até MAX_WORKERS (1 = Sequencial, 2+ = Paralelo)
        for num_workers in range(1, MAX_WORKERS + 1):
            print(f"\n[Avaliando {num_workers} Processador(es)...]")

            for rep in range(1, REPETITIONS + 1):
                elapsed_time = execute_parallel(num_workers, COMPLEXITY)

                # Registra no log
                writer.writerow([rep, num_workers, f"{elapsed_time:.4f}"])
                csv_file.flush()  # Garante gravação imediata no disco

                print(
                    f" -> Repetição {rep:2d}/{REPETITIONS} | "
                    f"Workers: {num_workers:2d} | Tempo: {elapsed_time:.2f}s"
                )

    print("\n" + "=" * 60)
    print(f"Benchmark finalizado com sucesso! Log salvo em: {LOG_FILENAME}")
    print("=" * 60)
