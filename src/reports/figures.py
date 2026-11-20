"""
Figuras del documento sobre los perfiles finales (temporada completa).

perfiles_zonas.png   jugadores en el plano profundidad x distancia al eje central, por perfil, con los
                     umbrales del árbol sustituto que separa los perfiles por zona de actuación
perfiles_rasgos.png  diferencia estandarizada de las variables que más distinguen a cada perfil

Los colores identifican a cada perfil y son los mismos en el documento, el casebook y el pitch.
Salida: reports/figures/
"""

from __future__ import annotations

import json

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.config import ROOT, path  # noqa: E402

COLORS = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}
INK, INK2, MUTED, RULE = "#1a1a1a", "#4a4a4a", "#8a8a8a", "#dcdcdc"
OUT = ROOT / "reports" / "figures"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": RULE,
        "axes.labelcolor": INK2,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)


def zones(cards: dict) -> None:
    a = pd.read_parquet(path("models") / "profiles_full_assignments.parquet")
    f = pd.read_parquet(path("features") / "player_features_full.parquet")
    d = a.merge(
        f[["player_id", "competition_file", "loc_depth", "loc_width"]], on=["player_id", "competition_file"]
    )
    fig, ax = plt.subplots(figsize=(6.6, 3.9), dpi=200)
    for p in (1, 2, 3):
        g = d[d.profile == p]
        ax.scatter(
            g.loc_depth, g.loc_width, s=9, color=COLORS[p], alpha=0.75, linewidths=0.3, edgecolors="white"
        )
    # umbrales del árbol sustituto (composición y localización)
    ax.axvline(50.2, color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.plot([25, 50.2], [29.3, 29.3], color=MUTED, lw=0.8, ls=(0, (4, 3)))
    ax.plot([50.2, 75], [34.3, 34.3], color=MUTED, lw=0.8, ls=(0, (4, 3)))
    names = {p["profile"]: p["name"] for p in cards["profiles"]}
    for p, (x, y) in {1: (27, 13), 2: (27, 44), 3: (62, 13)}.items():
        n = next(c["n"] for c in cards["profiles"] if c["profile"] == p)
        ax.text(x, y, f"{names[p]}\n{n} jugadores", color=INK, fontsize=8.5, fontweight="bold", va="center")
        ax.scatter([x - 1.2], [y + 1.6], s=26, color=COLORS[p])
    ax.set_xlim(25, 75)
    ax.set_ylim(8, 48)
    ax.set_xlabel("Profundidad media de sus acciones (0 propia portería, 100 portería rival)")
    ax.set_ylabel("Distancia media al eje central")
    ax.grid(color="#efefef", lw=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(OUT / "perfiles_zonas.png")
    plt.close(fig)


def traits(cards: dict) -> None:
    rows = []  # (perfil, etiqueta, z) en bloques por perfil, de arriba hacia abajo
    for c in cards["profiles"]:
        for t in c["top_variables"][:6]:
            label = t["label"].replace(", % de sus acciones", " (% de acciones)").split(" (0")[0]
            rows.append((c["profile"], label, t["z"]))
    gap = 0.9
    ys, y = [], 0.0
    for i, (p, _, _) in enumerate(rows):
        if i and rows[i - 1][0] != p:
            y += gap
        ys.append(y)
        y += 1
    fig, ax = plt.subplots(figsize=(6.6, 5.4), dpi=200)
    for (p, _, z), yy in zip(rows, ys):
        ax.barh(yy, z, color=COLORS[p], height=0.62)
        ax.text(z + (0.04 if z > 0 else -0.04), yy, f"{z:+.2f}".replace(".", ","), va="center",
                ha="left" if z > 0 else "right", fontsize=7, color=INK2)  # fmt: skip
    ax.set_yticks(ys, [r[1] for r in rows], fontsize=7.5)
    ax.tick_params(axis="y", length=0, colors=INK2)
    ax.invert_yaxis()
    ax.axvline(0, color=INK2, lw=0.8)
    ax.set_xlim(-1.75, 1.75)
    ax.grid(axis="x", color="#efefef", lw=0.6)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    starts = {}
    for (p, _, _), yy in zip(rows, ys):
        starts.setdefault(p, yy)
    for c in cards["profiles"]:
        ax.text(1.75, starts[c["profile"]] - 0.8, c["name"], ha="right", va="bottom", fontsize=8.5,
                fontweight="bold", color=INK, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})  # fmt: skip
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
    ax.set_xlabel("Diferencia estandarizada frente al promedio de los 1.500 jugadores", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "perfiles_rasgos.png")
    plt.close(fig)


def main() -> None:
    cards = json.loads((path("models") / "profile_cards.json").read_text(encoding="utf-8"))
    zones(cards)
    traits(cards)
    print("reports/figures/perfiles_zonas.png, perfiles_rasgos.png")


if __name__ == "__main__":
    main()
