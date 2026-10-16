import os
import subprocess
import time
import zipfile
import numpy as np

# ==========================================
# CONFIGURAÇÃO: Quantidade de Sudokus
# ==========================================
NUM_SUDOKUS = 200  # Altere aqui o número desejado de sudokus para resolver


def obter_linhas_sudoku():
    zip_path = os.path.expanduser("~/Downloads/sudoku.zip")
    extract_dir = os.path.expanduser("~/Downloads")
    csv_path = os.path.join(extract_dir, "sudoku.csv")

    url = "https://www.kaggle.com/api/v1/datasets/download/bryanpark/sudoku"
    command = ["curl", "-L", "-o", zip_path, url]

    # 1. Download via curl se o arquivo ainda não existir no disco
    if not os.path.exists(csv_path):
        print(f"Downloading dataset to {zip_path}...")
        subprocess.run(command, check=True)
        print("Download complete!")

        # 2. Descompactação do arquivo sudoku.zip
        print(f"Extracting {zip_path}...")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)
        print(f"File extracted to {csv_path}")

    # 3. Leitura do arquivo CSV local
    print(f"Lendo dados de {csv_path}...")
    with open(csv_path, "r", encoding="utf-8") as f:
        conteudo = f.read().splitlines()

    return conteudo


# 1. Carrega os dados
content = obter_linhas_sudoku()

# 2. Processa os N primeiros sudokus (excluindo cabeçalho)
linhas = content[1 : NUM_SUDOKUS + 1]

quizzes = np.zeros((NUM_SUDOKUS, 81), dtype=np.int32)
solutions = np.zeros((NUM_SUDOKUS, 81), dtype=np.int32)

for i, line in enumerate(linhas):
    quiz, solution = line.split(",")
    for j, (q, s) in enumerate(zip(quiz, solution)):
        quizzes[i, j] = int(q)
        solutions[i, j] = int(s)

quizzes = quizzes.reshape((-1, 9, 9))
solutions = solutions.reshape((-1, 9, 9))


# 3. Algoritmo de Backtracking para resolver o Sudoku
def eh_valido(tabuleiro, lin, col, num):
    if num in tabuleiro[lin, :] or num in tabuleiro[:, col]:
        return False
    inicio_lin, inicio_col = 3 * (lin // 3), 3 * (col // 3)
    if num in tabuleiro[inicio_lin : inicio_lin + 3, inicio_col : inicio_col + 3]:
        return False
    return True


def resolver_sudoku(tabuleiro):
    vazios = np.argwhere(tabuleiro == 0)
    if len(vazios) == 0:
        return True  # Todos os quadros preenchidos

    lin, col = vazios[0]
    for num in range(1, 10):
        if eh_valido(tabuleiro, lin, col, num):
            tabuleiro[lin, col] = num
            if resolver_sudoku(tabuleiro):
                return True
            tabuleiro[lin, col] = 0  # Backtrack
    return False


# 4. Execução e validação dos N primeiros
print("\n" + "=" * 45)
print(f" RESOLVENDO OS {NUM_SUDOKUS} PRIMEIROS SUDOKUS")
print("=" * 45)

# Início da medição de tempo
tempo_inicio = time.perf_counter()

for idx in range(NUM_SUDOKUS):
    tabuleiro = quizzes[idx].copy()
    solucao_esperada = solutions[idx]

    if resolver_sudoku(tabuleiro):
        correto = np.array_equal(tabuleiro, solucao_esperada)
        status = "CORRETO" if correto else "INCORRETO"
        print(f"Sudoku #{idx + 1:02d}: Resolvido! [{status}]")
    else:
        print(f"Sudoku #{idx + 1:02d}: Não foi possível resolver.")

print("\nPrimeiro Sudoku Resolvido (Matriz 9x9):")
print(tabuleiro)

# Fim da medição e exibição do tempo total
tempo_fim = time.perf_counter()
tempo_decorrido = tempo_fim - tempo_inicio

print("\n" + "=" * 45)
print(f"Tempo total decorrido: {tempo_decorrido:.2f} segundos")
print("=" * 45)
print("\n\nPara fazer o profile deste código, execute no seu linux o seguinte comando:\n perf stat python3 ppd-sudoku.py")
print("\n\nPara fazer o profiler detalhado deste código, execute no seu linux o seguinte comando:\n python3 -m cProfile -s cumtime ppd-sudoku.py")

