import os
import sys
import subprocess

pasta = "Completos e Assimetricos nos Arcos"
arquivo_modelo = "ils.py"            
arquivo_saida = "resultados_ils.txt"

instancias = sorted(
    nome for nome in os.listdir(pasta)
    if nome.endswith(".atsp")
)

print(f"{len(instancias)} instâncias encontradas em '{pasta}'\n")

with open(arquivo_saida, "w", encoding="utf-8") as saida:
    for k, nome in enumerate(instancias, 1):
        print(f"[{k}/{len(instancias)}] Executando: {nome}", flush=True)

        subprocess.run(
            [sys.executable, arquivo_modelo],
            input=nome + "\n",
            text=True,
            stdout=saida,
            stderr=subprocess.STDOUT
        )
        saida.flush()   

print(f"\nResultados salvos em {arquivo_saida}")