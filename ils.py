import pulp
import os
import time
import random

LIM_TEMPO = 300

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
        viz = perturbar(atual, sem_melhora)          # Trocar pela função de pertubar (ainda não feito)
        viz, c_viz = busca_local_2opt(viz, w, n)
        atual, c_atual = aceitar(atual, c_atual, viz, c_viz, sem_melhora)  # Trocar pela função de aceite (ainda não feito)

        if c_atual < c_melhor:
            melhor, c_melhor, sem_melhora = atual[:], c_atual, 0
        else:
            sem_melhora += 1

    assert viavel(melhor, n, S, T)
    return melhor, c_melhor, time.time() - t0

pasta = "Completos e Assimetricos nos Arcos"
nome_arquivo = input()
caminho_completo = os.path.join(pasta, nome_arquivo)

w = parse_atsp_file(caminho_completo)
n = len(w)




