import os
import time
import random

LIM_TEMPO = 300
TEMPO_ILS = 10          # segundos por execução do ILS
SEEDS = range(3)        # seeds por configuração


def parse_atsp_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    dimension = 0
    weight_section = False
    flat_weights = []
    for line in lines:
        line_str = line.strip()
        if line_str.startswith('DIMENSION:'):
            dimension = int(line_str.split(':')[1].strip())
        elif line_str.startswith('EDGE_WEIGHT_SECTION'):
            weight_section = True
            continue
        elif line_str.startswith('EOF'):
            break
        if weight_section:
            numbers = [int(x) for x in line_str.split()]
            flat_weights.extend(numbers)
    # Reconstrói a matriz bidimensional n x n
    w = []
    for i in range(dimension):
        w.append(flat_weights[i * dimension:(i + 1) * dimension])
    return w


def custo(c, w):
    return sum(w[c[i]][c[i+1]] for i in range(len(c) - 1))


def viavel(c, n, S, T):
    return c[0] == S and c[-1] == T and sorted(c) == list(range(n))


def busca_local_2opt(c, w, n):
    c = c[:]
    atual = custo(c, w)
    while True:
        melhor_delta, mi, mj = 0, -1, -1
        for i in range(1, n - 2):
            p = c[i-1]
            fwd = 0   # custo do segmento c[i..j] no sentido original
            rev = 0   # custo do mesmo segmento invertido
            for j in range(i + 1, n - 1):
                fwd += w[c[j-1]][c[j]]
                rev += w[c[j]][c[j-1]]
                s = c[j+1]
                old = w[p][c[i]] + fwd + w[c[j]][s]
                new = w[p][c[j]] + rev + w[c[i]][s]
                if new - old < melhor_delta:
                    melhor_delta, mi, mj = new - old, i, j
        if mi == -1:
            break
        c[mi:mj+1] = c[mi:mj+1][::-1]
        atual += melhor_delta
    return c, atual


# Heuristica
def vizinho_mais_proximo(w, S, T):
    """
    Constrói um caminho S -> ... -> T visitando todos os vértices.
    A cada passo vai para o vizinho não visitado de menor custo w[u][v].
    Tratamento do vértice T: ele fica reservado e só entra por último.
    (O grafo é completo, então nunca existe beco sem saída.)
    """
    n = len(w)
    nao_visitados = set(range(n)) - {S, T}
    caminho = [S]
    u = S
    while nao_visitados:
        v = min(nao_visitados, key=lambda x: w[u][x])
        caminho.append(v)
        nao_visitados.remove(v)
        u = v
    caminho.append(T)
    return caminho


# Perturbação 
def double_bridge(c):
    """Double-bridge no interior do caminho: A|B|C -> A|C|B (S e T fixos)."""
    interior = c[1:-1]
    m = len(interior)
    if m < 3:
        return c[:]
    p1, p2 = sorted(random.sample(range(1, m), 2))
    A, B, C = interior[:p1], interior[p1:p2], interior[p2:]
    return [c[0]] + A + C + B + [c[-1]]


def k_trocas(c, k):
    """k trocas aleatórias de posições interiores (S e T fixos)."""
    novo = c[:]
    if len(novo) < 4:
        return novo
    for _ in range(k):
        i, j = random.sample(range(1, len(novo) - 1), 2)
        novo[i], novo[j] = novo[j], novo[i]
    return novo


def criar_perturbacao(tipo="double_bridge", forca=1, passo=50, forca_max=5):
    """
    Devolve a função perturbar(atual, sem_melhora) usada pelo ILS.
    A força é adaptativa: começa em 'forca' e sobe 1 a cada 'passo'
    iterações sem melhora (até 'forca_max'), para escapar de platôs.
    """
    def perturbar(atual, sem_melhora):
        f = min(forca + sem_melhora // passo, forca_max)
        if tipo == "double_bridge":
            novo = atual
            for _ in range(f):
                novo = double_bridge(novo)
            return novo
        return k_trocas(atual, f + 1)
    return perturbar


# Critérios de aceitação 

def criar_aceite_melhor():
    """Aceita somente se não piorar."""
    def aceitar(atual, c_atual, viz, c_viz, sem_melhora):
        return (viz, c_viz) if c_viz <= c_atual else (atual, c_atual)
    return aceitar


def criar_aceite_sa(T0=0.01, alpha=0.999):
    """
    Estilo Simulated Annealing: piora aceita com prob. exp(-delta/T).
    T é relativo ao custo atual (T_efetivo = T * c_atual), então a mesma
    configuração funciona em instâncias com escalas de custo diferentes.
    """
    estado = {"T": T0}
    def aceitar(atual, c_atual, viz, c_viz, sem_melhora):
        delta = c_viz - c_atual
        T_ef = max(estado["T"] * c_atual, 1e-12)
        estado["T"] *= alpha
        if delta <= 0 or random.random() < pow(2.718281828, -delta / T_ef):
            return viz, c_viz
        return atual, c_atual
    return aceitar


def criar_aceite_restart(w, S, T, limite=100):
    """
    Aceita só melhora/empate. Após 'limite' rejeições seguidas, REINICIA:
    troca a solução atual por uma aleatória (S e T fixos).
    """
    n = len(w)
    estado = {"rej": 0}
    def aceitar(atual, c_atual, viz, c_viz, sem_melhora):
        if c_viz <= c_atual:
            estado["rej"] = 0
            return viz, c_viz
        estado["rej"] += 1
        if estado["rej"] >= limite:
            estado["rej"] = 0
            interior = list(range(n))
            interior.remove(S)
            interior.remove(T)
            random.shuffle(interior)
            novo = [S] + interior + [T]
            return novo, custo(novo, w)
        return atual, c_atual
    return aceitar


# =====================================================================
#                   ILS (Pessoa A) - inalterado
# =====================================================================

def ils(w, S, T, sol_inicial, perturbar, aceitar,
    tempo_max=60, max_iter=None, seed=0):
    random.seed(seed)
    n = len(w)
    atual, c_atual = busca_local_2opt(sol_inicial, w, n)
    melhor, c_melhor = atual[:], c_atual
    it, sem_melhora = 0, 0
    t0 = time.time()

    while time.time() - t0 < tempo_max and (max_iter is None or it < max_iter):
        it += 1
        viz = perturbar(atual, sem_melhora)
        viz, c_viz = busca_local_2opt(viz, w, n)
        atual, c_atual = aceitar(atual, c_atual, viz, c_viz, sem_melhora)

        if c_atual < c_melhor:
            melhor, c_melhor, sem_melhora = atual[:], c_atual, 0
        else:
            sem_melhora += 1

    assert viavel(melhor, n, S, T)
    return melhor, c_melhor, time.time() - t0


# =====================================================================
#                              Execução
# =====================================================================
if __name__ == "__main__":
    pasta = "Completos e Assimetricos nos Arcos"
    nome_arquivo = input()
    caminho_completo = os.path.join(pasta, nome_arquivo)

    w = parse_atsp_file(caminho_completo)
    n = len(w)
    S, T = 0, n - 1

    print("##########################################")
    print("Instancia: " + nome_arquivo)

    # Heurística inicial
    t0 = time.perf_counter()
    sol0 = vizinho_mais_proximo(w, S, T)
    t_heur = time.perf_counter() - t0
    assert viavel(sol0, n, S, T)
    print(f"Heurística inicial (NN): custo = {custo(sol0, w)} | tempo = {t_heur:.4f}s")

    configs = {
        "ILS-melhor":  lambda: criar_aceite_melhor(),
        "ILS-SA":      lambda: criar_aceite_sa(T0=0.01, alpha=0.999),
        "ILS-restart": lambda: criar_aceite_restart(w, S, T, limite=100),
    }

    for nome, fab in configs.items():
        custos = []
        for sd in SEEDS:
            perturbar = criar_perturbacao("double_bridge", forca=1)
            _, c, t = ils(w, S, T, sol0, perturbar, fab(),
                          tempo_max=TEMPO_ILS, seed=sd)
            custos.append(c)
        print(f"{nome}: melhor = {min(custos)} | média = {sum(custos)/len(custos):.1f} "
              f"| custos = {custos}")