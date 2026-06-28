import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib as mpl

# =====================
# Global Font: Times New Roman
# =====================
mpl.rcParams["font.family"] = "serif"
mpl.rcParams["font.serif"] = ["Times New Roman"]
mpl.rcParams["mathtext.fontset"] = "stix"
mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42

# =====================
# RGB Colors
# =====================
deep_blue = (47/255, 82/255, 142/255)
deep_purple = (112/255, 48/255, 160/255)
axis_gray = (194/255, 194/255, 194/255)

# =====================
# Data
# =====================
noise_std = [0.001, 0.005, 0.01, 0.03, 0.05, 0.1]
noise_acc = [0.9694, 0.9682, 0.9659, 0.9531, 0.9338, 0.8621]

bit_width = [32, 16, 12, 8, 6, 4]
quant_acc = [0.9698, 0.9705, 0.9701, 0.9694, 0.9537, 0.7781]

# =====================
# Style helpers
# =====================
def nsr_axis_style(ax):
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)

    ax.spines["bottom"].set_linewidth(1.2)
    ax.spines["bottom"].set_color(axis_gray)

    ax.tick_params(
        axis="x",
        which="both",
        direction="in",
        length=4,
        width=1.2,
        color=axis_gray,
        labelcolor="black",
        pad=4
    )
    ax.tick_params(axis="y", length=0)
    ax.grid(False)


def annotate_above_with_bbox(ax, xs, ys, dy_points=16, fmt="{:.2f}"):
    for i, (x, y) in enumerate(zip(xs, ys)):
        off = dy_points if i % 2 == 0 else dy_points + 4
        ax.annotate(
            fmt.format(y * 100),
            xy=(x, y),
            xytext=(0, off),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
            color="black",
            bbox=dict(
                boxstyle="round,pad=0.15",
                facecolor="white",
                edgecolor="none",
                alpha=1.0
            ),
            zorder=5
        )

# ===============================
# (a) Noise robustness
# ===============================
fig = plt.figure(figsize=(4.2, 2.6))

plt.plot(
    noise_std,
    noise_acc,
    marker="s",
    linewidth=4,
    markersize=9,
    color=deep_blue,
    label="Acc [%]",
    zorder=3
)

ax = plt.gca()
nsr_axis_style(ax)

ax.set_xscale("log")
ax.set_xticks([0.001, 0.01, 0.1])
ax.set_xticklabels(["0.001", "0.01", "0.1"])

ax.set_xticks(noise_std, minor=True)
ax.xaxis.set_minor_formatter(mticker.NullFormatter())

ax.set_ylim(min(noise_acc) - 0.04, max(noise_acc) + 0.06)

annotate_above_with_bbox(ax, noise_std, noise_acc, dy_points=16)

plt.xlabel("SD of random noise values", fontsize=12, labelpad=6)
plt.title("a", loc="left", fontweight="bold")
plt.legend(frameon=False, loc="lower left", handlelength=3)

plt.tight_layout()

fig.savefig("Fig_a_noise.pdf", bbox_inches="tight")
fig.savefig("Fig_a_noise.tiff", dpi=600, bbox_inches="tight")

plt.show()

# ===============================
# (b) Quantization sensitivity
# ===============================
fig = plt.figure(figsize=(4.2, 2.6))

xpos = list(range(len(bit_width)))

plt.plot(
    xpos,
    quant_acc,
    marker="s",
    linewidth=4,
    markersize=9,
    color=deep_purple,
    label="Acc [%]",
    zorder=3
)

ax = plt.gca()
nsr_axis_style(ax)

ax.set_xticks(xpos)
ax.set_xticklabels([str(b) for b in bit_width])

ax.set_ylim(min(quant_acc) - 0.06, max(quant_acc) + 0.06)

annotate_above_with_bbox(ax, xpos, quant_acc, dy_points=16)

plt.xlabel("Number of weight bits", fontsize=12, labelpad=6)
plt.title("b", loc="left", fontweight="bold")
plt.legend(frameon=False, loc="lower left", handlelength=3)

plt.tight_layout()

fig.savefig("Fig_b_quantization.pdf", bbox_inches="tight")
fig.savefig("Fig_b_quantization.tiff", dpi=600, bbox_inches="tight")

plt.show()