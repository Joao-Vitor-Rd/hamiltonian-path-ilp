import os
import sys
import csv
import glob
import time
import pulp

TEMPO_LIMITE = 180 

def parse_atsp_file(filepath):
    dimension = 0
    in_weights = False
    flat = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("DIMENSION"):
                dimension = int(line.split(":")[1].strip())
            elif line.startswith("EDGE_WEIGHT_SECTION"):
                in_weights = True
            elif line.startswith("EOF"):
                break
            elif in_weights:
                flat.extend(int(x) for x in line.split())
    return [flat[i * dimension:(i + 1) * dimension] for i in range(dimension)]

def verificar_caminho(arcos, w, s=None, t=None):
    """
    arcos: lista de tuplas (i, j), vértices numerados de 0 a n-1.
    Retorna (eh_valido, custo_total, mensagem).
    """
    n = len(w)
    s = 0 if s is None else s
    t = n - 1 if t is None else t

    if len(arcos) != n - 1:
        return False, None, f"Esperados {n - 1} arcos, recebidos {len(arcos)}."

    sucessor = {}
    entradas = set()
    for (i, j) in arcos:
        if not (0 <= i < n and 0 <= j < n) or i == j:
            return False, None, f"Arco inválido ({i}, {j})."
        if i in sucessor:
            return False, None, f"Vértice {i} tem mais de um arco de saída."
        if j in entradas:
            return False, None, f"Vértice {j} tem mais de um arco de entrada."
        sucessor[i] = j
        entradas.add(j)

    if s in entradas:
        return False, None, "Existe arco entrando na origem."
    if t in sucessor:
        return False, None, "Existe arco saindo do destino."
    if s not in sucessor:
        return False, None, "Nenhum arco sai da origem."

    visitados = [s]
    atual = s
    while atual in sucessor:
        atual = sucessor[atual]
        if atual in visitados:
            return False, None, "Ciclo detectado."
        visitados.append(atual)

    if atual != t:
        return False, None, "O caminho não termina no destino."
    if len(visitados) != n:
        return False, None, "O caminho não visita todos os vértices (subrotas)."

    custo = sum(w[i][j] for (i, j) in arcos)
    return True, custo, "Caminho viável."

def construir_modelo(w, inteiro=True):
    n = len(w)
    S, T = 0, n - 1
    cat = pulp.LpInteger if inteiro else pulp.LpContinuous

    m = pulp.LpProblem("PCHM_MTZ", pulp.LpMinimize)

    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0, upBound=1, cat=cat)
         for i in range(n) for j in range(n) if i != j}
    u = {i: pulp.LpVariable(f"u_{i}", lowBound=1 if i == S else 2,
                            upBound=1 if i == S else n, cat=pulp.LpContinuous)
         for i in range(n)}

    m += pulp.lpSum(w[i][j] * x[i, j] for (i, j) in x)

    m += pulp.lpSum(x[S, j] for j in range(n) if j != S) == 1
    m += pulp.lpSum(x[i, T] for i in range(n) if i != T) == 1
    m += pulp.lpSum(x[i, S] for i in range(n) if i != S) == 0
    m += pulp.lpSum(x[T, j] for j in range(n) if j != T) == 0

    for k in range(n):
        if k in (S, T):
            continue
        m += pulp.lpSum(x[i, k] for i in range(n) if i != k) == 1
        m += pulp.lpSum(x[k, j] for j in range(n) if j != k) == 1

    for i in range(n):
        for j in range(n):
            if i != j and j != S:
                m += u[i] - u[j] + n * x[i, j] <= n - 1

    return m, x, u


def resolver(m, tempo_limite=None):
    solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=tempo_limite)
    t0 = time.time()
    m.solve(solver)
    return time.time() - t0


def extrair_arcos(x):
    return [(i, j) for (i, j), v in x.items()
            if v.value() is not None and v.value() > 0.5]


def rodar_instancia(caminho):
    w = parse_atsp_file(caminho)
    n = len(w)
    nome = os.path.splitext(os.path.basename(caminho))[0]
    res = {"instancia": nome, "n": n}
    
    m_lp, _, _ = construir_modelo(w, inteiro=False)
    t_lp = resolver(m_lp)
    res["status_LP"] = pulp.LpStatus[m_lp.status]
    res["valor_LP"] = pulp.value(m_lp.objective)
    res["tempo_LP_s"] = round(t_lp, 2)
    
    m_ip, x_ip, _ = construir_modelo(w, inteiro=True)
    t_ip = resolver(m_ip, TEMPO_LIMITE)
    res["status_IP"] = pulp.LpStatus[m_ip.status]
    res["tempo_IP_s"] = round(t_ip, 2)
    res["otimo_provado"] = (m_ip.sol_status == pulp.LpSolutionOptimal)

    arcos = extrair_arcos(x_ip)
    valido, custo, msg = verificar_caminho(arcos, w)
    res["solucao_valida"] = valido
    res["valor_IP"] = custo if valido else None

    if valido and custo and res["valor_LP"] is not None:
        res["gap_%"] = round(100 * (custo - res["valor_LP"]) / custo, 2)
    else:
        res["gap_%"] = None
    return res


def main():
    alvo = sys.argv[1] if len(sys.argv) > 1 else "Completos e Assimetricos nos Arcos"
    if os.path.isdir(alvo):
        arquivos = sorted(glob.glob(os.path.join(alvo, "*.atsp")))
    else:
        arquivos = [alvo]

    resultados = []
    for arq in arquivos:
        print(f"Resolvendo {arq} ...", flush=True)
        r = rodar_instancia(arq)
        print(r, flush=True)
        resultados.append(r)

    if resultados:
        with open("resultados.csv", "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(resultados[0].keys()))
            wr.writeheader()
            wr.writerows(resultados)
        print("\nResultados salvos em resultados.csv")


if __name__ == "__main__":
    main()