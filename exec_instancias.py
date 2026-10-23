import os
import sys
import subprocess

pasta = "Completos e Assimetricos nos Arcos"
arquivo_modelo = "chm-mtz.py"
arquivo_saida = "resultados_5_min_int.txt"

# Obtém todas as instâncias .atsp da pasta
instancias = sorted(
    nome for nome in os.listdir(pasta)
    if nome.endswith(".atsp")
)

with open(arquivo_saida, "w", encoding="utf-8") as saida:
    for nome in instancias:
        print(f"Executando: {nome}")

        subprocess.run(
            [sys.executable, arquivo_modelo],
            input=nome + "\n",
            text=True,
            stdout=saida,
            stderr=subprocess.STDOUT
        )

print(f"\nResultados salvos em {arquivo_saida}")
