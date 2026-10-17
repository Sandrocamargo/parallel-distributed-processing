# Relatório Técnico: Avaliação de Paralelismo em Tarefas Intensivas de CPU em Python

**Disciplina:** Programação Paralela e Distribuída

**Professores:** Sandro Camargo e Leonardo Pinho

---

## 1. Funcionamento do Código Avaliado

O experimento avaliou o desempenho computacional dividindo uma carga de trabalho pesada entre múltiplos *workers*. O trecho de código responsável pelo processamento é composto por duas funções encadeadas:

```python
import math


def heavy_task(n):
    """Tarefa CPU-bound que simula um processamento pesado sem usar sleep().

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

```

### Explicação do Algoritmo

1. **`heavy_task(n)`:** Esta função representa a **carga de trabalho computacional pura** (*CPU-bound*).
* **Sem bloqueios artificiais:** O código evita o uso de `time.sleep()`, que apenas colocaria a *thread* em estado de espera (liberando a CPU). Em vez disso, ele mantém a CPU a 100% de uso calculando operações de ponto flutuante.
* **Custo Computacional:** A cada iteração do laço `for`, a CPU calcula a raiz quadrada (`math.sqrt(i)`) e o seno (`math.sin(i)`), acumulando o produto na variável `total`. Trata-se de uma carga determinística que exige ciclos intensivos da unidade de ponto flutuante (FPU) do processador.


2. **`run_chunk(args)`:** Atua como a **interface de mapeamento (*worker wrapper*)**.
* Quando utilizamos gerenciadores de execução paralela (`ProcessPoolExecutor` ou `ThreadPoolExecutor`), as fatias da carga de trabalho são empacotadas em tuplas de argumentos (`args`).
* A função desempacota o valor $n$ correspondente àquela fatia (`sub_n`) e invoca a execução da rotina matemática, retornando o resultado parcial para o processo principal.



---

## 2. A Problemática do *Global Interpreter Lock* (GIL) em CPython

Na linguagem Python, especificamente na sua implementação padrão (CPython), a execução concorrente por meio de *threads* nativas do sistema operacional é estritamente limitada pelo mecanismo do **GIL (*Global Interpreter Lock*)**. O impacto dessa limitação varia conforme o paradigma de concorrencia e a natureza da carga de trabalho:

- **Tarefas *I/O-bound* (Operações de Rede e Disco):** O GIL é liberado temporariamente enquanto as *threads* aguardam respostas externas do sistema operacional, permitindo uma concorrência eficiente e ganhos substanciais de desempenho.
- **Tarefas *CPU-bound* (como o algoritmo `heavy_task`):** Como os laços de repetição demandam processamento contínuo de *bytecodes*, as *threads* entram em intensa **disputa pelo *lock* (*lock contention*)**. Consequentemente, apenas **uma única *thread*** consegue executar código Python por vez dentro do mesmo processo, inviabilizando o uso de múltiplos núcleos físicos de CPU via `ThreadPoolExecutor` (`threads(GIL)`).

Para contornar essa limitação em tarefas *CPU-bound*, foram avaliadas abordagens baseadas em múltiplos processos (`processos` com `multiprocessing.Pool` e `threads(poolexecutor)` com `ProcessPoolExecutor`). Nesses modelos, cada *worker* é alocado em um processo independente, dispondo de seu próprio interpretador CPython e, por conseguinte, de um GIL isolado, o que viabiliza o paralelismo real e o uso efetivo de múltiplos núcleos de processamento.


---

## 3. Análise dos Resultados Empíricos

O conjunto de dados `benchmark_paralelismo.csv` registra **600 execuções** (compostas por 20 configurações distintas de quantidade de *workers*, submetidas a 10 repetições para cada um dos 3 modos de execução avaliados: `processos`, `threads(GIL)` e `threads(poolexecutor)`).

#### Tabela 1: Métricas de Desempenho Média por Quantidade de Workers ($p$)

| Workers ($p$) | Proc. Tempo (s) | Proc. $S_p$ | Proc. $E_p$ | Thread (GIL) Tempo (s) | Thread (GIL) $S_p$ | Thread (GIL) $E_p$ | PoolExec. Tempo (s) | PoolExec. $S_p$ | PoolExec. $E_p$ |
| :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| **1** | 7,5766 | 1,00x | 100,0% | 7,3698 | 1,00x | 100,0% | 7,4665 | 1,00x | 100,0% |
| **2** | 4,0560 | 1,87x | 93,4% | 7,4883 | 0,98x | 49,2% | 4,1009 | 1,82x | 91,0% |
| **3** | 2,8606 | 2,65x | 88,3% | 7,6125 | 0,97x | 32,3% | 2,9483 | 2,53x | 84,4% |
| **4** | 2,1963 | 3,45x | 86,2% | 7,5599 | 0,97x | 24,4% | 2,2824 | 3,27x | 81,8% |
| **6** | 2,1354 | 3,55x | 59,1% | 7,5284 | 0,98x | 16,3% | 2,1759 | 3,43x | 57,2% |
| **8** | 2,1952 | 3,45x | 43,1% | 7,4772 | 0,99x | 12,3% | 2,1448 | 3,48x | 43,5% |
| **10** | 2,1207 | 3,57x | 35,7% | 7,4996 | 0,98x | 9,8% | 2,1552 | 3,46x | 34,6% |
| **12** | 2,1890 | 3,46x | 28,8% | 7,4527 | 0,99x | 8,2% | 2,1411 | 3,49x | 29,1% |
| **16** | 2,1183 | 3,58x | 22,4% | 7,4287 | 0,99x | 6,2% | 2,1391 | 3,49x | 21,8% |
| **20** | 2,1420 | 3,54x | 17,7% | 7,4975 | 0,98x | 4,9% | 2,1558 | 3,46x | 17,3% |


---

## 4. Visualização Gráfica do Desempenho

As figuras abaixo apresentam graficamente os resultados da comparação de desempenho.

### Figura 1: Comparação do Tempo de Execução entre Processos e Threads
![Tempo](images/1_comparacao_tempo_execucao.png)

### Figura 2: Análise de SpeedUp
![SpeedUp](images/2_comparacao_speedup.png)

### Figura 3: Eficiência da Paralelização
![Eficiencia](images/3_comparacao_eficiencia.png)

---

## 5. Discussão e Conclusões Técnicas

### 5.1 Desempenho com Processos (`processos` e `threads(poolexecutor)`)

- **Ganho Escalar Significativo:** No intervalo de $1$ a $4$ *workers*, observa-se uma redução consistente no tempo médio de execução em ambas as abordagens baseadas em processos. No modo `processos` (`multiprocessing.Pool`), o tempo cai de **7,58 s** para **2,20 s** ($S_p = 3,45\text{x}$; $E_p = 86,2\%$). No modo `threads(poolexecutor)` (`ProcessPoolExecutor`), o tempo reduz de **7,47 s** para **2,28 s** ($S_p = 3,27\text{x}$; $E_p = 81,8\%$).
- **Saturação de Hardware e Escalabilidade:** O desempenho máximo é atingido entre $4$ e $6$ *workers*, onde os tempos de execução se estabilizam na faixa de **2,12 s a 2,18 s** em ambos os modos. A estabilização do *speedup* em aproximadamente **3,55x** evidencia que a arquitetura do processador dispõe de **4 núcleos físicos de processamento**; a adição de *workers* além desse limite não gera ganhos adicionais devido ao *overhead* de alternância de contexto (*context switching*) e ao escalonamento de processos pelo sistema operacional.

### 5.2 Desempenho com Threads (`threads(GIL)`)

- **Estagnação e Degradação Relativa:** O uso de `ThreadPoolExecutor` para uma carga estritamente matemática (*CPU-bound*) demonstrou a ineficácia do paralelismo via *threads* em CPython. O tempo de execução permaneceu praticamente constante em todas as configurações, variando de **7,37 s** ($p=1$) a **7,61 s** ($p=3$), mantendo o *speedup* estagnado próximo a **0,97x–1,00x**.
- **Mecanismo de Contenda do GIL:** Como a função `heavy_task` consome ciclos ininterruptos de CPU executando *bytecodes*, as *threads* entram em disputa constante pela posse do *lock* do GIL (*lock contention*). O custo de sincronização e chaveamento entre *threads* sem a capacidade de execução paralela em múltiplos núcleos faz com que a eficiência despenque progressivamente à medida que $p$ aumenta, caindo de **100,0%** ($p=1$) para apenas **4,9%** ($p=20$).

### 5.3 Conclusão

Os resultados empíricos ratificam a distinção fundamental entre **concorrência** e **paralelismo real** no ecossistema Python. Para tarefas intensivas de processamento matemático (*CPU-bound*), o modelo de **múltiplos processos isolados** — seja via `multiprocessing.Pool` ou `ProcessPoolExecutor` — é estritamente necessário para contornar as limitações do GIL e obter escalabilidade real na arquitetura *multicore* dos processadores modernos.


### 6. Replicação do experimento

Para aumentar ou reduzir a complexidade do experimento, para alterar o tempo de execução, altere o parâmetro **complexidade** no arquivo **0params.cfg**.

Para executar o experimento, execute o comando: **python3 1paralelo.py**.

Para realizar a análise estatística e gerar os gráficos, execute o comando: **python3 2analisa.py**.
