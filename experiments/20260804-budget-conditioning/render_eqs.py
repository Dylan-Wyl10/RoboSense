"""Render display equations for the deck as tight PNGs (matplotlib mathtext).

Conservative mathtext only (\\frac, \\sum, subscripts, \\lceil ): no LaTeX install
needed. Output: results/eq/*.png on the deck's surface colour.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = f"{HERE}/results/eq"
os.makedirs(OUT, exist_ok=True)

INK = "#0b0b0b"

EQS = {
    # objectives, before and after
    "eq_old": (r"$\min_{R}\ \ \frac{\alpha_1 \sum_v C_v(R)\ -\ "
               r"\alpha_2 \sum_{(i,\tau)} y_{i\tau}(R)}{V \cdot H}"
               r"\qquad \mathrm{s.t.}\ \ \mathrm{vehicle}\ v\ "
               r"\mathrm{arrives\ at}\ d_v\ \mathrm{by}\ H$", 21),
    "eq_new": (r"$\min_{R}\ \ \frac{\alpha_1 \sum_v C_v(R)\ -\ "
               r"\alpha_2 \sum_{(i,\tau)} y_{i\tau}(R)}{\sum_v B_v}"
               r"\qquad \mathrm{s.t.}\ \ \mathrm{vehicle}\ v\ "
               r"\mathrm{arrives\ at}\ d_v\ \mathrm{by}\ t_{0v}+B_v$", 21),
    # rigorous slides
    "eq_def": (r"$f_\alpha(R)\ =\ \frac{\alpha_1 C(R)\ -\ \alpha_2 K(R)}{N},"
               r"\qquad C(R)=\sum_v C_v(R),\quad "
               r"K(R)=\left|\,\bigcup_v \mathrm{cells}(R_v)\right|,"
               r"\quad N>0\ \mathrm{const.}$", 20),
    "eq_lemma": (r"$0\ \leq\ K(R)\ \leq\ C(R)\qquad\mathrm{and}\qquad "
                 r"K(R{+}\mathrm{detour\ of\ length}\ k)\ \leq\ K(R)+k$", 20),
    "eq_collapse": (r"$K(R)=C(R)\ \ \Rightarrow\ \ f_\alpha(R)\ =\ "
                    r"\frac{(\alpha_1-\alpha_2)}{N}\,C(R)$", 22),
    "eq_prop1": (r"$C(R)\ >\ C^{*}\ +\ "
                 r"\frac{\alpha_2\,(C^{*}-K_0)}{\alpha_1-\alpha_2}"
                 r"\ \ \Rightarrow\ \ f_\alpha(R)\ >\ f_\alpha(R_0)$", 20),
    "eq_prop2": (r"$\Delta f\ =\ \frac{\alpha_1 k\ -\ \alpha_2\,\Delta K}{N}"
                 r"\ <\ 0\ \ \Longleftrightarrow\ \ \Delta K\ >\ "
                 r"\frac{\alpha_1}{\alpha_2}\,k$", 20),
    # budget assignment (two stacked lines)
    "eq_budget": (r"$B_v\ =\ \min\!\left(\ \max\!\left(\ "
                  r"\lceil  \rho_v\, \tau^{min}_v \rceil,\ \tau^{min}_v\right),"
                  r"\ H-t_{0v}\right)$", 19),
    "eq_taumin": (r"$\tau^{min}_v\ =\ \mathrm{EarliestArrival}"
                  r"(o_v \to d_v\ \mid\ t_{0v},\ \delta)\ -\ t_{0v}"
                  r"\qquad \mathrm{(time{-}dependent\ Dijkstra)}$", 19),
}


def main():
    for name, (tex, size) in EQS.items():
        fig = plt.figure(figsize=(0.1, 0.1), dpi=200)
        fig.patch.set_alpha(0.0)
        t = fig.text(0, 0, tex, fontsize=size, color=INK)
        fig.canvas.draw()
        bb = t.get_window_extent()
        fig.set_size_inches(bb.width / 200 + 0.08, bb.height / 200 + 0.08)
        fig.savefig(f"{OUT}/{name}.png", transparent=True,
                    bbox_inches="tight", pad_inches=0.03)
        plt.close(fig)
        print(name, "ok")


if __name__ == "__main__":
    main()
