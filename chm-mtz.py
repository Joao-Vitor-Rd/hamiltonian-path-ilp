import pulp
import os
import time

LIM_TEMPO = 300

def validar_caminho_hamiltoniano(caminho, n, S, T, w=None, valor_objetivo=None):

    # 1. S deve ter sucessor
    if S not in caminho:
        return False, f"Vértice inicial {S} não possui arco de saída."

    # 2. T não pode ter sucessor
    if T in caminho:
        return False, f"Vértice final {T} possui arco de saída ({T}, {caminho[T]})."

    # 3. Ninguém pode apontar para S
    if S in caminho.values():
        return False, f"Existe arco entrando no vértice inicial {S}."

    # 4. Cada vértice deve ter no máximo uma entrada
    if len(set(caminho.values())) != len(caminho):
        return False, "Algum vértice possui mais de um arco de entrada."

    # 5. Percorre o caminho a partir de S
    visitados = [S]
    conjunto = {S}
    atual = S
    custo = 0

    while atual != T:
        if atual not in caminho:
            return False, f"Caminho interrompido no vértice {atual} (sem sucessor)."

        prox = caminho[atual]

        if not (0 <= prox < n):
            return False, f"Vértice {prox} fora do intervalo [0, {n - 1}]."

        if prox == atual:
            return False, f"Laço no vértice {atual}."

        if prox in conjunto:
            return False, f"Ciclo detectado: vértice {prox} visitado duas vezes."

        if w is not None:
            custo += w[atual][prox]

        visitados.append(prox)
        conjunto.add(prox)
        atual = prox

    # 6. Deve visitar todos os vértices
    if len(visitados) != n:
        faltando = sorted(set(range(n)) - conjunto)
        return False, f"Caminho não é hamiltoniano. Vértices não visitados: {faltando}"

    # 7. Todos os arcos de 'caminho' devem pertencer ao percurso
    #    (evita subciclos isolados que o MTZ deveria barrar)
    if len(caminho) != n - 1:
        return False, (f"Existem arcos fora do caminho principal "
                       f"({len(caminho)} arcos, esperado {n - 1}).")

    # 8. Confere o custo, se fornecido
    if w is not None and valor_objetivo is not None:
        if abs(custo - valor_objetivo) > 1e-6:
            return False, (f"Custo do caminho ({custo}) difere do valor "
                           f"objetivo do solver ({valor_objetivo}).")

    return True, f"Caminho hamiltoniano válido. Custo = {custo}"

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


pasta = "Completos e Assimetricos nos Arcos"
nome_arquivo = input()
caminho_completo = os.path.join(pasta, nome_arquivo)


w = parse_atsp_file(caminho_completo)
n = len(w)

S = 0
T = n-1

m = pulp.LpProblem("Caminho-hamitoniano", pulp.LpMinimize)

# variaveis
x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", 0, 1, pulp.LpInteger)
     for i in range(n) for j in range(n) if i != j}

u = {i: pulp.LpVariable(f"u_{i}", 1, n - 1, pulp.LpContinuous)
     for i in range(1, n)}

# Função Objetivo --------------------------------

m += pulp.lpSum(x[i, j] * w[i][j] for i in range(n) for j in range(n) if i != j)

# Restrições ------------------------------

# R1 - Não entra nenhum arco em S
m += pulp.lpSum(x[i, S] for i in range(1, n)) == 0

# R2 - Só sai de um arco de S 
m += pulp.lpSum(x[S, i] for i in range(1, n)) == 1

# R3 - Só entra um arco em T 
m += pulp.lpSum(x[i, T] for i in range(0, T)) == 1

# R4 - Não sai nenhum arco em T
m += pulp.lpSum(x[T, i] for i in range(0, T)) == 0

# R5 - entra apenas 1 arco em cada vértice intermediario 
# R6 - sai apenas 1 arco em cada vértice intermediario 
for j in range(1,T):
    m += pulp.lpSum(x[i, j] for i in range(n) if i != j) == 1
    m += pulp.lpSum(x[j, i] for i in range(n) if i != j) == 1

# R7- MTZ

for i in range(1, n):
    for j in range(1, n):
        if i != j:
            m += u[i] - u[j] + n * x[i, j] <= n - 1

print("##########################################")
print("Instancia: " + nome_arquivo)

inicio = time.perf_counter()

m.solve(pulp.PULP_CBC_CMD(
    msg=False,
    timeLimit=LIM_TEMPO,
    gapRel=0
))

fim = time.perf_counter()

tempo_execucao = fim - inicio

print(f"Tempo de execução: {tempo_execucao:.4f} segundos")

status = pulp.LpStatus[m.status]

sol_status = m.sol_status
estourou_tempo = tempo_execucao >= LIM_TEMPO - 1.0

if sol_status == pulp.LpSolutionOptimal and not estourou_tempo:
    classificacao = "ÓTIMO PROVADO"
elif sol_status in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible):
    classificacao = "NÃO ÓTIMO (melhor solução viável até o limite de tempo)"
elif sol_status == pulp.LpSolutionInfeasible:
    classificacao = "INVIÁVEL"
else:
    classificacao = "NENHUMA SOLUÇÃO ENCONTRADA"

print("Status PuLP:", pulp.LpStatus[m.status])
print("sol_status:", sol_status)
print("Classificação:", classificacao)
print("Valor objetivo:", pulp.value(m.objective))


caminho = {}

for (i, j), v in x.items():
    if v.value() > 0.5:
        caminho[i] = j

print(validar_caminho_hamiltoniano(
    caminho, n, S, T,
    w=w,
    valor_objetivo=pulp.value(m.objective)
))

act_vertice = S

while act_vertice != T:
    print(f"({act_vertice}, {caminho[act_vertice]})")
    act_vertice = caminho[act_vertice]
