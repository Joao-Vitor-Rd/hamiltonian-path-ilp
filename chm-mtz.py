import pulp
import os

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
nome_arquivo = "br17.atsp"
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

m.solve(pulp.PULP_CBC_CMD(msg=True))
print(pulp.LpStatus[m.status], pulp.value(m.objective))
for (i, j), v in x.items():
    if v.value() > 0.5:
        print(f"arco ({i} -> {j})")