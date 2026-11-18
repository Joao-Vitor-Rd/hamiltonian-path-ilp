"""
Lê o resultado do PLI (TP01) e do ILS (TP02) e calcula o gap de cada instância.
Gera: resultados_gap.csv, grafico_gap.png e grafico_gap_ils.png

Uso:  python3 analisar.py
"""
import re
import csv

ARQ_PLI = "resultados_5_min_int.txt"     # saída do chm-mtz.py (PLI)
ARQ_ILS = "resultados_ils.txt"           # saída do exec_ils.py (ILS)
CONFIGS = ["ILS-melhor", "ILS-SA", "ILS-restart"]


def ler_pli(arq):
    """Devolve {instancia: (valor_objetivo, classificacao, tempo)}."""
    dados, inst = {}, None
    with open(arq, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("Instancia:"):
                inst = linha.split(":", 1)[1].strip()
                dados[inst] = [None, "", None]
            elif inst and linha.startswith("Valor objetivo:"):
                v = linha.split(":", 1)[1].strip()
                try:
                    dados[inst][0] = float(v)
                except ValueError:
                    dados[inst][0] = None
            elif inst and linha.startswith("Classificação:"):
                dados[inst][1] = linha.split(":", 1)[1].strip()
            elif inst and linha.startswith("Tempo de execução:"):
                m = re.search(r"([\d.]+)", linha)
                dados[inst][2] = float(m.group(1)) if m else None
    return dados


def ler_ils(arq):
    """Devolve {instancia: {'nn': custo, 'ILS-xxx': (melhor, media)}}."""
    dados, inst = {}, None
    with open(arq, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha.startswith("Instancia:"):
                inst = linha.split(":", 1)[1].strip()
                dados[inst] = {}
            elif inst and linha.startswith("Heurística inicial"):
                m = re.search(r"custo = (\d+)", linha)
                if m:
                    dados[inst]["nn"] = float(m.group(1))
            elif inst:
                m = re.match(r"(ILS-\w+): melhor = (\d+) \| média = ([\d.]+)", linha)
                if m:
                    dados[inst][m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return dados


def gap(valor, ref):
    return 100.0 * (valor - ref) / ref if ref else None


pli = ler_pli(ARQ_PLI)
ils = ler_ils(ARQ_ILS)

linhas = []
for inst in sorted(ils):
    if inst not in pli or pli[inst][0] is None:
        print(f"Aviso: {inst} sem valor do PLI, ignorada.")
        continue
    ref, classif, t_pli = pli[inst]
    reg = {"instancia": inst, "pli": ref,
           "otimo": "sim" if "PROVADO" in classif.upper() and "NÃO" not in classif.upper() else "não",
           "t_pli": t_pli, "nn": ils[inst].get("nn"),
           "gap_nn": gap(ils[inst].get("nn"), ref) if ils[inst].get("nn") else None}
    for c in CONFIGS:
        if c in ils[inst]:
            melhor, media = ils[inst][c]
            reg[f"{c}_melhor"] = melhor
            reg[f"{c}_media"] = media
            reg[f"{c}_gap"] = gap(media, ref)
    linhas.append(reg)

if not linhas:
    raise SystemExit("Nenhuma instância em comum entre os dois arquivos.")

# ---------- CSV ----------
campos = ["instancia", "pli", "otimo", "t_pli", "nn", "gap_nn"]
for c in CONFIGS:
    campos += [f"{c}_melhor", f"{c}_media", f"{c}_gap"]
with open("resultados_gap.csv", "w", newline="", encoding="utf-8") as f:
    wr = csv.DictWriter(f, fieldnames=campos)
    wr.writeheader()
    wr.writerows(linhas)

# ---------- Tabela no terminal ----------
print(f"\n{'Instância':<14}{'PLI':>8}{'Ótimo':>7}{'NN':>8}{'gapNN%':>8}", end="")
for c in CONFIGS:
    print(f"{c[4:]+' gap%':>14}", end="")
print()
for r in linhas:
    print(f"{r['instancia']:<14}{r['pli']:>8.0f}{r['otimo']:>7}{(r['nn'] or 0):>8.0f}"
          f"{(r['gap_nn'] or 0):>8.1f}", end="")
    for c in CONFIGS:
        g = r.get(f"{c}_gap")
        print(f"{(g if g is not None else float('nan')):>14.2f}", end="")
    print()

print("\nGap médio (%) sobre as instâncias:")
print(f"  Heurística inicial (NN): {sum(r['gap_nn'] for r in linhas if r['gap_nn'] is not None)/len(linhas):.2f}")
for c in CONFIGS:
    gs = [r[f"{c}_gap"] for r in linhas if r.get(f"{c}_gap") is not None]
    if gs:
        venceu = sum(1 for r in linhas if r.get(f"{c}_melhor") is not None and r[f"{c}_melhor"] <= r["pli"])
        print(f"  {c}: {sum(gs)/len(gs):.2f}  (melhor execução igualou ou superou o PLI em {venceu}/{len(linhas)})")

# ---------- Gráficos ----------
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def tamanho(nome):
        """Número no nome da instância (ftv33 -> 33), usado para ordenar por porte."""
        m = re.search(r"(\d+)", nome)
        return int(m.group(1)) if m else 0

    ordem = sorted(linhas, key=lambda r: tamanho(r["instancia"]))
    # '*' marca instâncias em que o PLI NÃO provou otimalidade (estourou o tempo)
    rotulos = [r["instancia"].replace(".atsp", "") + ("*" if r["otimo"] == "não" else "")
               for r in ordem]
    cores = {"NN": "#9E9E9E", "ILS-melhor": "#1F77B4", "ILS-SA": "#FF7F0E", "ILS-restart": "#2CA02C"}

    def desenhar(series, titulo, arquivo, valores=False):
        fig, ax = plt.subplots(figsize=(max(10, len(ordem) * 0.95), 5.8))
        k = len(series)
        larg = 0.8 / k
        for idx, (rot, chave) in enumerate(series):
            vals = [r.get(chave) if r.get(chave) is not None else 0 for r in ordem]
            xs = [i - 0.4 + larg * (idx + 0.5) for i in range(len(ordem))]
            barras = ax.bar(xs, vals, larg * 0.92, label=rot, color=cores[rot], zorder=3)
            if valores:
                for b, v in zip(barras, vals):
                    ax.annotate(f"{v:.1f}", (b.get_x() + b.get_width() / 2, v),
                                xytext=(0, 3 if v >= 0 else -10), textcoords="offset points",
                                ha="center", fontsize=7, rotation=90)
        ax.axhline(0, color="black", linewidth=1, zorder=4)
        ax.set_xticks(range(len(ordem)))
        ax.set_xticklabels(rotulos, rotation=45, ha="right")
        ax.set_ylabel("Gap para o PLI (%)")
        ax.set_title(titulo, fontsize=13, fontweight="bold")
        ax.grid(axis="y", linestyle="--", alpha=0.4, zorder=0)
        ax.set_axisbelow(True)
        for lado in ("top", "right"):
            ax.spines[lado].set_visible(False)
        ax.legend(frameon=False, ncol=k, loc="upper left")
        ymin, ymax = ax.get_ylim()
        ax.set_ylim(ymin, ymax * 1.08)
        fig.text(0.01, 0.01,
                 "Instâncias ordenadas pelo porte.  * = PLI não provou o ótimo (limite de tempo); "
                 "gap negativo = ILS melhor que o PLI.",
                 fontsize=8, color="#555555")
        fig.tight_layout(rect=(0, 0.03, 1, 1))
        fig.savefig(arquivo, dpi=200)
        plt.close(fig)

    ils_series = [(c, f"{c}_gap") for c in CONFIGS]
    desenhar([("NN", "gap_nn")] + ils_series,
             "Heurística inicial e ILS: gap em relação ao PLI", "grafico_gap.png")
    desenhar(ils_series,
             "ILS: gap em relação ao PLI (média das seeds)", "grafico_gap_ils.png", valores=True)
    print("\nGráficos salvos em grafico_gap.png e grafico_gap_ils.png")
except ImportError:
    print("\n(matplotlib não instalado: gráficos não gerados. Use: pip install matplotlib)")

print("Arquivos gerados: resultados_gap.csv")