#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HMI ĐỘNG HỌC CƠ CẤU PHẲNG n KHÂU  (Python + matplotlib + CustomTkinter)
======================================================================
Cài thư viện :  pip install numpy scipy matplotlib customtkinter
Chạy         :  python mechanism_hmi.py

Ý tưởng
-------
Cơ cấu được MÔ TẢ BẰNG DỮ LIỆU (điểm, thanh, điểm gắn trên khâu) chứ không viết cứng
công thức cho cơ cấu 4 khâu. Bộ giải dùng ràng buộc khoảng cách:

    vị trí  :  |Pi - Pj|^2 - L^2 = 0                  (Newton - Raphson)
    vận tốc :  d . (vi - vj) = 0                       (hệ tuyến tính)
    gia tốc :  d . (ai - aj) = -|vi - vj|^2            (hệ tuyến tính)

với d = Pi - Pj. Thêm khâu  =  thêm điểm tự do + 2 thanh. Quy ước dấu: dương = NGƯỢC chiều
kim đồng hồ, góc φ2 đo từ trục x dương.

Loại điểm
---------
  cố định  : nối giá, tọa độ (x, y)
  tay quay : đầu khâu dẫn, tham số (tên điểm tâm quay, bán kính r); quay với φ2, ω2, ε2
  tự do    : khớp chưa biết, tọa độ (x, y) chỉ là GIÁ TRỊ ĐOÁN ĐẦU (chọn nhánh lắp ráp)
Thanh      : cặp điểm (i, j) và độ dài L (một ràng buộc khoảng cách)
Điểm gắn   : điểm M, E... gắn trên khâu cứng (i, j): s = khoảng dọc theo i->j,
             t = khoảng vuông góc (t > 0 nằm bên trái chiều i->j). i, j phải cùng một khâu cứng
             (khâu có 3 khớp thì thêm thanh thứ 3 để tạo tam giác cứng).
Điều kiện giải được: số thanh = 2 x số điểm tự do.
"""
from __future__ import annotations

import copy
import itertools
import json
import math

import numpy as np
from scipy.optimize import least_squares

from matplotlib.figure import Figure
from matplotlib.patches import Arc, FancyArrowPatch, Polygon

# ====================================================================================
# 1. BỘ GIẢI TỔNG QUÁT
# ====================================================================================


def rot90(v):
    """Quay vector 90° ngược chiều kim đồng hồ."""
    return np.array([-v[1], v[0]])


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _num(x, what):
    try:
        return float(str(x).replace(",", "."))
    except ValueError:
        raise ValueError(f"'{x}' không phải số ({what})") from None


class Mechanism:
    """Cơ cấu phẳng n khâu mô tả bằng dữ liệu (dict, xem PRESETS bên dưới)."""

    def __init__(self, data):
        self.fixed, self.free0, self.cranks = {}, {}, {}
        self.bars, self.locals = [], {}
        names = set()
        for p in data["points"]:
            n = str(p["name"]).strip()
            if not n:
                raise ValueError("Có điểm chưa đặt tên")
            if n in names:
                raise ValueError(f"Trùng tên điểm '{n}'")
            names.add(n)
            kind = p["kind"]
            if kind in ("fixed", "free"):
                xy = np.array([_num(p["a"], f"x của {n}"), _num(p["b"], f"y của {n}")])
                (self.fixed if kind == "fixed" else self.free0)[n] = xy
            elif kind == "crank":
                self.cranks[n] = (str(p["a"]).strip(), _num(p["b"], f"r của {n}"))
            else:
                raise ValueError(f"Loại điểm không hợp lệ: {kind}")
        if not self.cranks:
            raise ValueError("Cần ít nhất 1 điểm loại 'tay quay' (khâu dẫn)")
        for n, (c, r) in self.cranks.items():
            if c not in self.fixed:
                raise ValueError(f"Tâm quay '{c}' của {n} phải là điểm cố định")
            if r <= 0:
                raise ValueError(f"Bán kính của {n} phải > 0")
        for b in data["bars"]:
            i, j = str(b["i"]).strip(), str(b["j"]).strip()
            if i not in names or j not in names:
                raise ValueError(f"Thanh {i}-{j}: điểm không tồn tại")
            if i == j:
                raise ValueError(f"Thanh {i}-{j}: hai đầu trùng nhau")
            L = _num(b["L"], f"độ dài {i}{j}")
            if L <= 0:
                raise ValueError(f"Độ dài {i}{j} phải > 0")
            self.bars.append((i, j, L))
        self.free_names = list(self.free0)
        if len(self.bars) != 2 * len(self.free_names):
            raise ValueError(
                f"Số thanh phải = 2 × số điểm tự do (hiện {len(self.bars)} thanh, "
                f"{len(self.free_names)} điểm tự do ⇒ cần {2 * len(self.free_names)} thanh)")
        bodies, _ = self.bodies()
        for q in data.get("locals", []):
            n = str(q["name"]).strip()
            if not n:
                continue
            if n in names:
                raise ValueError(f"Trùng tên điểm '{n}'")
            names.add(n)
            i, j = str(q["i"]).strip(), str(q["j"]).strip()
            if not any(i in b and j in b for b in bodies):
                raise ValueError(f"Điểm {n}: {i} và {j} phải thuộc cùng một khâu cứng")
            self.locals[n] = (i, j, _num(q["s"], f"s của {n}"), _num(q["t"], f"t của {n}"))
        self.reset_guess()

    # ---------------------------------------------------------------- cấu trúc
    def reset_guess(self):
        self.guess = {n: p.copy() for n, p in self.free0.items()}

    def all_bars(self):
        """Danh sách (i, j) của mọi khâu: tay quay trước, rồi các thanh."""
        return [(c, n) for n, (c, _) in self.cranks.items()] + [(i, j) for i, j, _ in self.bars]

    def bodies(self):
        """Gộp các thanh tạo thành tam giác thành 1 khâu cứng. Trả (list tập điểm, chỉ số khâu của mỗi thanh)."""
        bars = self.all_bars()
        parent = list(range(len(bars)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        pair = {frozenset(b): k for k, b in enumerate(bars)}
        pts = sorted({p for b in bars for p in b})
        for a, b, c in itertools.combinations(pts, 3):
            ks = [pair.get(frozenset(x)) for x in ((a, b), (b, c), (a, c))]
            if all(k is not None for k in ks):
                parent[find(ks[1])] = find(ks[0])
                parent[find(ks[2])] = find(ks[0])
        groups = {}
        for k, b in enumerate(bars):
            groups.setdefault(find(k), set()).update(b)
        roots = list(groups)
        return [groups[r] for r in roots], [roots.index(find(k)) for k in range(len(bars))]

    def structure_report(self):
        bodies, _ = self.bodies()
        n = len(bodies)
        all_pts = list(self.fixed) + list(self.free0) + list(self.cranks)
        p5 = 0
        for pt in all_pts:
            k = sum(pt in b for b in bodies) + (1 if pt in self.fixed else 0)
            p5 += max(k - 1, 0)
        W = 3 * n - 2 * p5
        # Phân tách nhóm Assur (heuristic): điểm tự do nào nối với >= 2 điểm đã biết là nhóm loại II
        known, remaining, order = set(self.fixed) | set(self.cranks), set(self.free0), []
        progress = True
        while remaining and progress:
            progress = False
            for p in sorted(remaining):
                nb = {j if i == p else i for i, j, _ in self.bars if p in (i, j)} & known
                if len(nb) >= 2:
                    order.append((p, sorted(nb)))
                    known.add(p)
                    remaining.discard(p)
                    progress = True
                    break
        lines = [
            f"Số khâu động            n  = {n}",
            f"Số khớp thấp            p5 = {p5}",
            f"Bậc tự do (Grübler)     W  = 3n - 2p5 = {W}" + ("" if W == 1 else "   ⚠ nên bằng 1"),
            f"Số ẩn tọa độ = {2 * len(self.free0)},  số phương trình thanh = {len(self.bars)}",
            "Phân tách nhóm Assur:   khâu dẫn " + ("".join(f"+ nhóm II[{p}←{'+'.join(nb)}] " for p, nb in order) or ""),
        ]
        if remaining:
            lines.append("Xếp loại: loại ≥ III (có nhóm không tách được thành nhóm 2 khâu 3 khớp)")
        else:
            lines.append(f"Xếp loại: cơ cấu loại II ({len(order)} nhóm Assur loại II)")
        return lines

    # ---------------------------------------------------------------- giải
    def _matrix(self, Q, factor):
        idx = {n: k for k, n in enumerate(self.free_names)}
        M = np.zeros((len(self.bars), 2 * len(idx)))
        for k, (i, j, _) in enumerate(self.bars):
            d = Q[i] - Q[j]
            if i in idx:
                M[k, 2 * idx[i]:2 * idx[i] + 2] += factor * d
            if j in idx:
                M[k, 2 * idx[j]:2 * idx[j] + 2] -= factor * d
        return M

    def solve(self, phi, w, e):
        """Trả (kết quả | None, thông báo). phi [rad], w [rad/s], e [rad/s^2]."""
        P = {n: p.copy() for n, p in self.fixed.items()}
        V = {n: np.zeros(2) for n in P}
        A = {n: np.zeros(2) for n in P}
        for n, (c, r) in self.cranks.items():
            rv = r * np.array([math.cos(phi), math.sin(phi)])
            P[n] = P[c] + rv
            V[n] = w * rot90(rv)
            A[n] = e * rot90(rv) - w * w * rv

        idx = {n: k for k, n in enumerate(self.free_names)}

        def full(x):
            Q = dict(P)
            for n, k in idx.items():
                Q[n] = x[2 * k:2 * k + 2]
            return Q

        def fun(x):
            Q = full(x)
            return np.array([(Q[i] - Q[j]) @ (Q[i] - Q[j]) - L * L for i, j, L in self.bars])

        if idx:
            x0 = np.concatenate([self.guess[n] for n in self.free_names])
            sol = least_squares(fun, x0, jac=lambda x: self._matrix(full(x), 2.0), method="lm",
                                xtol=1e-14, ftol=1e-14, gtol=1e-14)
            if np.max(np.abs(sol.fun)) > 1e-8:
                return None, f"Cơ cấu không lắp được tại φ₂ = {math.degrees(phi) % 360:.1f}°"
            P = full(sol.x)
            P = {n: np.array(p, float) for n, p in P.items()}
            for n in idx:
                V[n], A[n] = np.zeros(2), np.zeros(2)

            M = self._matrix(P, 1.0)
            if np.linalg.cond(M) > 1e10:
                return None, f"Vị trí kỳ dị tại φ₂ = {math.degrees(phi) % 360:.1f}° (không giải được v, a)"

            def known(Z, i, j, d):
                zi = np.zeros(2) if i in idx else Z[i]
                zj = np.zeros(2) if j in idx else Z[j]
                return d @ (zi - zj)

            b = np.array([-known(V, i, j, P[i] - P[j]) for i, j, _ in self.bars])
            xv = np.linalg.solve(M, b)
            for n, k in idx.items():
                V[n] = xv[2 * k:2 * k + 2]
            b = np.array([-np.sum((V[i] - V[j]) ** 2) - known(A, i, j, P[i] - P[j]) for i, j, _ in self.bars])
            xa = np.linalg.solve(M, b)
            for n, k in idx.items():
                A[n] = xa[2 * k:2 * k + 2]
            for n in idx:                        # ghi nhớ nghiệm để bám nhánh khi quay tiếp
                self.guess[n] = P[n].copy()

        # điểm gắn trên khâu: P = (1-a)Pi + a Pj + b R90(Pj - Pi)   (tuyến tính ⇒ dùng chung cho v, a)
        for n, (i, j, s, t) in self.locals.items():
            L = np.linalg.norm(P[j] - P[i])
            a_, b_ = s / L, t / L
            comb = lambda Z: (1 - a_) * Z[i] + a_ * Z[j] + b_ * rot90(Z[j] - Z[i])
            P[n], V[n], A[n] = comb(P), comb(V), comb(A)

        links = {}
        for (i, j) in self.all_bars():
            d, dv, da = P[j] - P[i], V[j] - V[i], A[j] - A[i]
            links[i + j] = dict(i=i, j=j, omega=cross(d, dv) / (d @ d), eps=cross(d, da) / (d @ d))
        return dict(P=P, V=V, A=A, links=links, phi=phi, w=w, e=e), "OK"

    def assemble(self, phi, w=0.0, e=0.0):
        """Lắp cơ cấu; nếu giá trị đoán đầu sai thì thử ngẫu nhiên nhiều lần."""
        res, msg = self.solve(phi, w, e)
        if res is not None:
            return res, msg
        rng = np.random.default_rng(1)
        R = sum(L for *_, L in self.bars) + sum(r for _, r in self.cranks.values())
        ctr = np.mean(list(self.fixed.values()), axis=0)
        for _ in range(400):
            self.guess = {n: ctr + rng.uniform(-R, R, 2) for n in self.free_names}
            res, msg = self.solve(phi, w, e)
            if res is not None:
                return res, msg
        self.reset_guess()
        return None, msg

    def sweep(self, phi0, w, e, step_deg=3.0):
        """Quét φ2 một vòng (hoặc đến giới hạn lắp) để vẽ đồ thị và chọn khung nhìn."""
        n = int(round(360 / step_deg))
        m = copy.deepcopy(self)
        out = {}
        full = True
        for k in range(n + 1):
            res, _ = m.solve(phi0 + math.radians(k * step_deg), w, e)
            if res is None:
                full = False
                break
            out[k * step_deg] = res
        if not full:
            m = copy.deepcopy(self)
            for k in range(1, n + 1):
                res, _ = m.solve(phi0 - math.radians(k * step_deg), w, e)
                if res is None:
                    break
                out[-k * step_deg] = res
        deg0 = math.degrees(phi0)
        keys = sorted(out, key=lambda k: (deg0 + k) % 360)
        return dict(phi=np.array([(deg0 + k) % 360 for k in keys]), results=[out[k] for k in keys])


def get_quantity(res, key):
    kind, name = key
    if kind == "omega":
        return res["links"][name]["omega"]
    if kind == "eps":
        return res["links"][name]["eps"]
    if kind == "v":
        return float(np.linalg.norm(res["V"][name]))
    return float(np.linalg.norm(res["A"][name]))


def quantity_options(m):
    """Danh sách đại lượng để vẽ đồ thị theo φ2:  {nhãn: (loại, tên)}."""
    q = {}
    for name in [i + j for i, j in m.all_bars()]:
        q[f"ω  {name}  (rad/s)"] = ("omega", name)
    for name in [i + j for i, j in m.all_bars()]:
        q[f"ε  {name}  (rad/s²)"] = ("eps", name)
    pts = [n for n in list(m.cranks) + m.free_names + list(m.locals)]
    for n in pts:
        q[f"|v{n}|  (m/s)"] = ("v", n)
    for n in pts:
        q[f"|a{n}|  (m/s²)"] = ("a", n)
    return q


# ====================================================================================
# 2. DỮ LIỆU MẪU
# ====================================================================================


def _circle_pick(p, r1, q, r2, upper=True):
    """Giao điểm của 2 đường tròn (tâm p bán kính r1, tâm q bán kính r2); chọn nghiệm phía trên/dưới."""
    p, q = np.array(p, float), np.array(q, float)
    d = np.linalg.norm(q - p)
    a = (r1 ** 2 - r2 ** 2 + d ** 2) / (2 * d)
    h = math.sqrt(max(r1 ** 2 - a ** 2, 0.0))
    base = p + a * (q - p) / d
    off = h * rot90((q - p) / d)
    c1, c2 = base + off, base - off
    return (c1 if (c1[1] >= c2[1]) == upper else c2)


def four_bar(L2, L3, BM, ME, L4, L1, phi_deg, w, e):
    """Cơ cấu 4 khâu của đề: A,D cố định; B tay quay; C tự do; M,E gắn trên BC (ME ⊥ BC, E ở phía dưới BC)."""
    B = L2 * np.array([math.cos(math.radians(phi_deg)), math.sin(math.radians(phi_deg))])
    C = _circle_pick(B, L3, (L1, 0), L4, upper=True)
    return {
        "points": [
            {"name": "A", "kind": "fixed", "a": 0, "b": 0},
            {"name": "D", "kind": "fixed", "a": L1, "b": 0},
            {"name": "B", "kind": "crank", "a": "A", "b": L2},
            {"name": "C", "kind": "free", "a": round(float(C[0]), 3), "b": round(float(C[1]), 3)},
        ],
        "bars": [{"i": "B", "j": "C", "L": L3}, {"i": "C", "j": "D", "L": L4}],
        "locals": [
            {"name": "M", "i": "B", "j": "C", "s": BM, "t": 0},
            {"name": "E", "i": "B", "j": "C", "s": BM, "t": -ME},
        ],
        "phi": phi_deg, "w": w, "e": e,           # w, e: dấu + = ngược chiều kim đồng hồ
    }


def extended_example():
    """Ví dụ n khâu: cơ cấu 4 khâu PA1 + thêm nhóm Assur (điểm F nối C và G cố định)."""
    d = four_bar(5.0, 4.5, 2.0, 1.0, 6.0, 3.0, 10, -5, -10)
    C = np.array([d["points"][3]["a"], d["points"][3]["b"]], float)
    G = np.array([6.0, 0.0])
    F = _circle_pick(C, 4.5, G, 5.5, upper=True)
    d["points"] += [
        {"name": "G", "kind": "fixed", "a": float(G[0]), "b": float(G[1])},
        {"name": "F", "kind": "free", "a": round(float(F[0]), 3), "b": round(float(F[1]), 3)},
    ]
    d["bars"] += [{"i": "C", "j": "F", "L": 4.5}, {"i": "F", "j": "G", "L": 5.5}]
    return d


# Theo Bảng 1 của đề:  PA1: ω2 = 5 cùng chiều KĐH, ε2 = 10 cùng chiều KĐH
#                      PA2: ω2 = 5 cùng chiều KĐH, ε2 = 20 ngược chiều KĐH   (bạn hãy đối chiếu lại với đề)
PRESETS = {
    "PA1 – cơ cấu 4 khâu": four_bar(5.0, 4.5, 2.0, 1.0, 6.0, 3.0, 10, -5, -10),
    "PA2 – cơ cấu 4 khâu": four_bar(5.0, 4.0, 2.5, 1.5, 6.0, 3.0, 20, -5, +20),
    "Ví dụ: 4 khâu + nhóm Assur (n = 5)": extended_example(),
}

# ====================================================================================
# 3. VẼ (matplotlib) - Hỗ trợ cả theme sáng và tối
# ====================================================================================

# Theme tối (mặc định)
BG_DARK, PANEL_DARK, GRID_DARK = "#12141a", "#1a1d25", "#2a2f3b"
TEXT_DARK, MUTED_DARK = "#e8ebf2", "#8b94a7"

# Theme sáng
BG_LIGHT, PANEL_LIGHT, GRID_LIGHT = "#f5f5f5", "#ffffff", "#d0d0d0"
TEXT_LIGHT, MUTED_LIGHT = "#1a1a1a", "#666666"

# Màu sắc dùng chung cho cả 2 theme
CYAN, PINK, GOLD, ORANGE, GREEN, RED = "#4cc9f0", "#f72585", "#ffd166", "#ff9f1c", "#06d6a0", "#ef476f"
COLORS = ["#4cc9f0", "#f72585", "#b5e48c", "#ffd166", "#9d4edd", "#ff9f1c", "#06d6a0", "#ef476f"]

# Biến theme hiện tại
BG, PANEL, GRID = BG_DARK, PANEL_DARK, GRID_DARK
TEXT, MUTED = TEXT_DARK, MUTED_DARK


def style_axes(ax, title, equal=True):
    """Style cho axes với màu sắc theo theme hiện tại"""
    global BG, PANEL, GRID, TEXT, MUTED
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=11, fontweight="bold", pad=8)
    ax.tick_params(colors=MUTED, labelsize=8)
    for s in ax.spines.values():
        s.set_color(GRID)
    ax.grid(True, color=GRID, lw=0.6, alpha=0.8)
    if equal:
        ax.set_aspect("equal", adjustable="box")


def view_from(results, margin=0.12):
    xs, ys = [], []
    for r in results:
        for p in r["P"].values():
            xs.append(p[0])
            ys.append(p[1])
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    mx, my = max((x1 - x0) * margin, 0.5), max((y1 - y0) * margin, 0.5)
    return (x0 - mx, x1 + mx), (y0 - my - 0.08 * (y1 - y0), y1 + my)


def draw_mechanism(ax, m, res, view, opts):
    """Vẽ lược đồ cơ cấu với màu sắc theo theme hiện tại"""
    global BG, PANEL, GRID, TEXT, MUTED
    ax.cla()
    style_axes(ax, "Lược đồ cơ cấu")
    P = res["P"]
    span = max(view[0][1] - view[0][0], view[1][1] - view[1][0])
    u = 0.028 * span
    bodies, bar_body = m.bodies()

    for k, body in enumerate(bodies):                              # tô nền khâu có >= 3 khớp
        if len(body) >= 3:
            pts = np.array([P[n] for n in body])
            c = pts.mean(0)
            pts = pts[np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))]
            ax.add_patch(Polygon(pts, closed=True, fc=COLORS[k % 8], alpha=0.16, ec="none", zorder=1))

    for k, (i, j) in enumerate(m.all_bars()):                      # các khâu
        a, b = P[i], P[j]
        col = COLORS[bar_body[k] % 8]
        # Màu viền tối hơn cho theme sáng
        edge_color = "#07080b" if BG == BG_DARK else "#ffffff"
        ax.plot([a[0], b[0]], [a[1], b[1]], color=edge_color, lw=10.5, solid_capstyle="round", zorder=2)
        ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=6.5, solid_capstyle="round", zorder=3)
        mid = (a + b) / 2
        ax.annotate(f"{i}{j}", mid, xytext=(0, 0), textcoords="offset points", ha="center", va="center",
                    color=edge_color, fontsize=8, fontweight="bold", zorder=4)

    for n in m.fixed:                                              # giá (ký hiệu gạch chéo)
        x, y = P[n]
        # Màu giá khác nhau cho theme sáng/tối
        support_color = "#2b303b" if BG == BG_DARK else "#e0e0e0"
        support_edge = "#9aa4b5" if BG == BG_DARK else "#666666"
        ax.add_patch(Polygon([[x, y], [x - 1.2 * u, y - 2.0 * u], [x + 1.2 * u, y - 2.0 * u]], closed=True,
                             fc=support_color, ec=support_edge, lw=1.2, zorder=4))
        hx, hy = [x - 1.8 * u, x + 1.8 * u, np.nan], [y - 2.0 * u, y - 2.0 * u, np.nan]
        for t in np.linspace(-1.8, 1.8, 7):                        # gạch chéo dưới chân giá (1 lần plot)
            hx += [x + t * u, x + (t - 0.55) * u, np.nan]
            hy += [y - 2.0 * u, y - 2.7 * u, np.nan]
        ax.plot(hx, hy, color=support_edge, lw=1.2, zorder=4)

    for n, (i, j, s, t) in m.locals.items():                       # điểm gắn trên khâu
        L = np.linalg.norm(P[j] - P[i])
        foot = (1 - s / L) * P[i] + (s / L) * P[j]
        ax.plot([foot[0], P[n][0]], [foot[1], P[n][1]], color=GOLD, lw=1.3, ls="--", zorder=4)
        ax.scatter(*P[n], marker="D", s=70, fc=GOLD, ec="#07080b" if BG == BG_DARK else "#ffffff", lw=1.2, zorder=6)

    for n in list(m.fixed) + list(m.cranks) + m.free_names:        # khớp
        ax.scatter(*P[n], s=120, fc=TEXT, ec="#07080b" if BG == BG_DARK else "#ffffff", lw=1.5, zorder=6)

    if opts.get("labels", True):
        for n, p in P.items():
            ax.annotate(n, p, xytext=(9, 9), textcoords="offset points", color=TEXT, fontsize=12,
                        fontweight="bold", zorder=8)

    deg = math.degrees(res["phi"]) % 360                           # góc φ2 tại tâm quay
    for n, (c, r) in m.cranks.items():
        cx, cy = P[c]
        rr = 0.14 * span
        ax.plot([cx, cx + 1.6 * rr], [cy, cy], color=MUTED, lw=1, ls="--", zorder=2)
        if deg > 0.5:
            ax.add_patch(Arc((cx, cy), 2 * rr, 2 * rr, theta1=0, theta2=deg, color=ORANGE, lw=1.8, zorder=5))
            ang = math.radians(deg / 2)
            ax.text(cx + 1.35 * rr * math.cos(ang), cy + 1.35 * rr * math.sin(ang), "φ₂", color=ORANGE,
                    fontsize=11, ha="center", va="center", zorder=8)

    for key, color, flag in (("V", CYAN, opts.get("show_v")), ("A", ORANGE, opts.get("show_a"))):
        if not flag:
            continue
        Z = res[key]
        mx = max((np.linalg.norm(z) for z in Z.values()), default=0) or 1.0
        k = 0.20 * span / mx
        for n, z in Z.items():
            if np.linalg.norm(z) > 1e-9:
                ax.add_patch(FancyArrowPatch(P[n], P[n] + k * z, arrowstyle="-|>", mutation_scale=13,
                                             color=color, lw=2, shrinkA=0, shrinkB=0, zorder=7))

    # Màu nền cho text box khác nhau cho theme sáng/tối
    text_bg = "#0c0d12" if BG == BG_DARK else "#ffffff"
    ax.text(0.02, 0.97, f"φ₂ = {deg:6.1f}°   ω₂ = {res['w']:+.2f} rad/s   ε₂ = {res['e']:+.2f} rad/s²",
            transform=ax.transAxes, color=TEXT, fontsize=9.5, va="top",
            bbox=dict(boxstyle="round,pad=0.35", fc=text_bg, ec=GRID))
    ax.set_xlim(view[0])
    ax.set_ylim(view[1])


def draw_plan(ax, m, res, key, title, pole):
    """Họa đồ vận tốc (key='V') hoặc gia tốc (key='A'): vector tuyệt đối từ cực + vector tương đối nét đứt."""
    global BG, PANEL, GRID, TEXT, MUTED
    ax.cla()
    style_axes(ax, title)
    Z = res[key]
    zero = [n for n, z in Z.items() if np.linalg.norm(z) < 1e-9]
    tips = {n: np.array(z) for n, z in Z.items() if n not in zero}

    def tip(n):
        return tips.get(n, np.zeros(2))

    for n, z in tips.items():
        ax.add_patch(FancyArrowPatch((0, 0), z, arrowstyle="-|>", mutation_scale=13, color=CYAN if key == "V"
                                     else ORANGE, lw=2.2, shrinkA=0, shrinkB=0, zorder=4))
        ax.annotate(n.lower(), z, xytext=(7, 7), textcoords="offset points", color=TEXT, fontsize=11,
                    fontweight="bold", zorder=6)
    for i, j in m.all_bars():                                       # vector tương đối giữa 2 đầu khâu
        if i in tips and j in tips:
            a, b = tips[i], tips[j]
            ax.plot([a[0], b[0]], [a[1], b[1]], color=PINK, lw=1.6, ls="--", zorder=3)
            mid = (a + b) / 2
            ax.annotate((i + j).lower(), mid, xytext=(0, -9), textcoords="offset points", ha="center",
                        color=PINK, fontsize=8, zorder=6)
    for n, (i, j, s, t) in m.locals.items():                        # định lý đồng dạng cho điểm gắn
        if n in tips:
            for h in (i, j):
                a = tip(h)
                ax.plot([a[0], tips[n][0]], [a[1], tips[n][1]], color=GOLD, lw=1.0, ls=":", zorder=3)
    # Màu viền cho theme sáng/tối
    pole_edge = "#07080b" if BG == BG_DARK else "#ffffff"
    ax.scatter([0], [0], s=60, fc=TEXT, ec=pole_edge, zorder=7)
    lbl = pole + (" ≡ " + ", ".join(n.lower() for n in zero) if zero else "")
    ax.annotate(lbl, (0, 0), xytext=(-8, -14), textcoords="offset points", color=TEXT, fontsize=10,
                ha="right", fontweight="bold", zorder=8)
    pts = np.array([[0, 0]] + [t for t in tips.values()])
    lo, hi = pts.min(0), pts.max(0)
    pad = 0.22 * max(hi[0] - lo[0], hi[1] - lo[1], 1e-6)
    if hi[0] - lo[0] < 1e-9 and hi[1] - lo[1] < 1e-9:
        lo, hi, pad = np.array([-1.0, -1.0]), np.array([1.0, 1.0]), 0
    ax.set_xlim(lo[0] - pad, hi[0] + pad)
    ax.set_ylim(lo[1] - pad, hi[1] + pad)


def draw_curve(ax, sweep, key, label, phi_deg, now):
    """Vẽ đồ thị với màu sắc theo theme hiện tại"""
    global BG, PANEL, GRID, TEXT, MUTED
    ax.cla()
    style_axes(ax, f"{label} theo φ₂", equal=False)
    if sweep and len(sweep["phi"]):
        y = np.array([get_quantity(r, key) for r in sweep["results"]])
        ax.plot(sweep["phi"], y, color=CYAN, lw=2.2, zorder=3)
        ax.fill_between(sweep["phi"], y, 0, color=CYAN, alpha=0.10, zorder=2)
        ax.axhline(0, color=MUTED, lw=0.8)
        ax.axvline(phi_deg % 360, color=ORANGE, lw=1.4, ls="--", zorder=4)
        # Màu viền cho theme sáng/tối
        dot_edge = "#07080b" if BG == BG_DARK else "#ffffff"
        ax.scatter([phi_deg % 360], [now], s=80, fc=ORANGE, ec=dot_edge, zorder=5)
        ax.annotate(f"{now:.3f}", (phi_deg % 360, now), xytext=(8, 8), textcoords="offset points",
                    color=ORANGE, fontsize=10, fontweight="bold")
    ax.set_xlim(0, 360)
    ax.set_xticks(range(0, 361, 45))
    ax.set_xlabel("φ₂ (độ)", color=MUTED)
    ax.set_ylabel(label, color=MUTED)


def direction_text(x):
    if abs(x) < 1e-9:
        return "—"
    return "ngược chiều kim đồng hồ" if x > 0 else "cùng chiều kim đồng hồ"


def report(m, res):
    L = ["KẾT QUẢ TÍNH TOÁN", "=" * 70,
         f"φ₂ = {math.degrees(res['phi']) % 360:.2f}°    ω₂ = {res['w']:+.4f} rad/s    ε₂ = {res['e']:+.4f} rad/s²",
         "(dấu + = ngược chiều kim đồng hồ)", "", "VẬN TỐC GÓC, GIA TỐC GÓC CỦA CÁC KHÂU", "-" * 70,
         f"{'Khâu':<6}{'ω (rad/s)':>12}  {'chiều ω':<25}{'ε (rad/s²)':>12}  chiều ε"]
    for name, lk in res["links"].items():
        L.append(f"{name:<6}{lk['omega']:>12.4f}  {direction_text(lk['omega']):<25}{lk['eps']:>12.4f}  "
                 f"{direction_text(lk['eps'])}")
    L += ["", "VẬN TỐC, GIA TỐC CÁC ĐIỂM  (hướng = góc so với trục x, độ)", "-" * 70,
          f"{'Điểm':<6}{'|v| (m/s)':>12}{'hướng v':>10}{'|a| (m/s²)':>14}{'hướng a':>10}"
          f"{'  vx':>10}{'vy':>9}{'ax':>10}{'ay':>9}"]
    for n in list(m.cranks) + m.free_names + list(m.locals):
        v, a = res["V"][n], res["A"][n]
        ang = lambda z: math.degrees(math.atan2(z[1], z[0])) if np.linalg.norm(z) > 1e-9 else float("nan")
        L.append(f"{n:<6}{np.linalg.norm(v):>12.4f}{ang(v):>10.2f}{np.linalg.norm(a):>14.4f}{ang(a):>10.2f}"
                 f"{v[0]:>10.3f}{v[1]:>9.3f}{a[0]:>10.3f}{a[1]:>9.3f}")
    L += ["", "TỌA ĐỘ CÁC ĐIỂM (m)", "-" * 70]
    for n, p in res["P"].items():
        L.append(f"{n:<6}x = {p[0]:>9.4f}   y = {p[1]:>9.4f}")
    L += ["", "PHÂN TÍCH CẤU TRÚC & XẾP LOẠI", "-" * 70] + m.structure_report()
    return "\n".join(L)


# ====================================================================================
# 4. GIAO DIỆN (CustomTkinter + matplotlib nhúng)
# ====================================================================================
import customtkinter as ctk                                         # noqa: E402
from tkinter import filedialog                                      # noqa: E402
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg     # noqa: E402

CCW, CW = "Ngược chiều KĐH", "Cùng chiều KĐH"
KIND_VI = {"fixed": "cố định", "free": "tự do", "crank": "tay quay"}
KIND_EN = {v: k for k, v in KIND_VI.items()}
T1, T2, T3 = "Lược đồ & họa đồ", "Đồ thị theo φ₂", "Kết quả"


def fmt(v):
    return v if isinstance(v, str) else f"{v:g}"


class ParamSlider(ctk.CTkFrame):
    """Nhãn + ô nhập số + thanh trượt đồng bộ với nhau."""

    def __init__(self, master, text, lo, hi, init, command):
        super().__init__(master, fg_color="transparent")
        self.lo, self.hi, self.command = lo, hi, command
        self.var = ctk.DoubleVar(value=init)
        self.entry_var = ctk.StringVar(value=fmt(init))
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=text, anchor="w").pack(side="left")
        self.entry = ctk.CTkEntry(top, width=78, height=26, textvariable=self.entry_var, justify="right")
        self.entry.pack(side="right")
        self.slider = ctk.CTkSlider(self, from_=lo, to=hi, variable=self.var, command=self._on_slide)
        self.slider.pack(fill="x", pady=(3, 8))
        self.entry.bind("<Return>", self._on_entry)
        self.entry.bind("<FocusOut>", self._on_entry)

    def _on_slide(self, v):
        self.entry_var.set(f"{float(v):.2f}")
        self.command()

    def _on_entry(self, _=None):
        try:
            v = float(self.entry_var.get().replace(",", "."))
        except ValueError:
            v = self.var.get()
        v = min(max(v, self.lo), self.hi)
        self.set(v)
        self.command()

    def set(self, v):
        self.var.set(v)
        self.entry_var.set(f"{v:.2f}".rstrip("0").rstrip("."))

    def get(self):
        return float(self.var.get())


class TableEditor(ctk.CTkFrame):
    """Bảng cho phép thêm / xóa / sửa dòng. columns = [(khóa, tiêu đề, độ rộng, danh sách lựa chọn | None)]."""

    def __init__(self, master, columns, height=120):
        super().__init__(master, fg_color="transparent")
        self.columns, self.rows = columns, []
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x")
        for _, title, width, _ in columns:
            ctk.CTkLabel(head, text=title, width=width, font=ctk.CTkFont(size=11), text_color=MUTED).pack(
                side="left", padx=1)
        # Màu nền scrollable frame theo theme
        body_bg = "#14161d" if BG == BG_DARK else "#f0f0f0"
        self.body = ctk.CTkScrollableFrame(self, height=height, fg_color=body_bg)
        self.body.pack(fill="x")
        btn_color = "#2a2f3b" if BG == BG_DARK else "#e0e0e0"
        btn_hover = "#39404f" if BG == BG_DARK else "#d0d0d0"
        ctk.CTkButton(self, text="＋ Thêm dòng", height=24, fg_color=btn_color, hover_color=btn_hover,
                      command=self.add_row).pack(anchor="w", pady=(4, 0))

    def add_row(self, values=None):
        values = values or {}
        row = ctk.CTkFrame(self.body, fg_color="transparent")
        row.pack(fill="x", pady=1)
        vs = {}
        for key, _, width, choices in self.columns:
            default = choices[0] if choices else ""
            v = ctk.StringVar(value=str(values.get(key, default)))
            if choices:
                w = ctk.CTkOptionMenu(row, values=choices, variable=v, width=width, height=26)
            else:
                w = ctk.CTkEntry(row, textvariable=v, width=width, height=26)
            w.pack(side="left", padx=1)
            vs[key] = v
        entry = (row, vs)
        ctk.CTkButton(row, text="✕", width=26, height=26, fg_color="#6b2b34", hover_color="#a33a48",
                      command=lambda: self.remove(entry)).pack(side="left", padx=(3, 0))
        self.rows.append(entry)

    def remove(self, entry):
        entry[0].destroy()
        self.rows.remove(entry)

    def set_rows(self, rows):
        for r in list(self.rows):
            self.remove(r)
        for r in rows:
            self.add_row(r)

    def get_rows(self):
        out = []
        for _, vs in self.rows:
            d = {k: v.get() for k, v in vs.items()}
            if any(str(x).strip() for k, x in d.items() if k != "kind"):
                out.append(d)
        return out


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("HMI động học cơ cấu phẳng n khâu")
        self.geometry("1540x900")
        self.minsize(1200, 740)
        self.configure(fg_color=BG)
        self.mech = self.res = self.sweep_data = self.view = None
        self.qopts, self.playing, self.play_dir, self._sweep_job = {}, False, 1, None
        self.is_dark_theme = True  # Trạng thái theme hiện tại
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self.load_preset(list(PRESETS)[0])

    # ------------------------------------------------------------------ chức năng theme
    def toggle_theme(self):
        """Chuyển đổi giữa theme sáng và tối"""
        global BG, PANEL, GRID, TEXT, MUTED
        
        self.is_dark_theme = not self.is_dark_theme
        
        if self.is_dark_theme:
            # Chuyển sang theme tối
            BG, PANEL, GRID = BG_DARK, PANEL_DARK, GRID_DARK
            TEXT, MUTED = TEXT_DARK, MUTED_DARK
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="☀️  Chuyển sang Theme Sáng")
        else:
            # Chuyển sang theme sáng
            BG, PANEL, GRID = BG_LIGHT, PANEL_LIGHT, GRID_LIGHT
            TEXT, MUTED = TEXT_LIGHT, MUTED_LIGHT
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="🌙  Chuyển sang Theme Tối")
        
        # Cập nhật màu nền cho cửa sổ chính
        self.configure(fg_color=BG)
        
        # Cập nhật màu cho matplotlib figures
        self.fig.set_facecolor(BG)
        self.fig2.set_facecolor(BG)
        
        # Cập nhật màu cho các widget CustomTkinter
        self._update_widget_colors()
        
        # Vẽ lại toàn bộ
        self.redraw()
        self.canvas.draw_idle()
        self.canvas2.draw_idle()
    
    def _update_widget_colors(self):
        """Cập nhật màu sắc cho tất cả các widget khi chuyển theme"""
        # Cập nhật màu nền cho sidebar
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.configure(fg_color=PANEL)
        
        # Cập nhật màu cho các nút
        btn_color = "#2a2f3b" if BG == BG_DARK else "#e0e0e0"
        btn_hover = "#39404f" if BG == BG_DARK else "#d0d0d0"
        
        # Cập nhật màu cho các nút trong sidebar
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=btn_color, hover_color=btn_hover)
        
        # Cập nhật màu cho textbox
        txt_bg = "#0f1116" if BG == BG_DARK else "#ffffff"
        if hasattr(self, 'txt'):
            self.txt.configure(fg_color=txt_bg)
        
        # Cập nhật màu cho các tab
        tv_bg = "#14161d" if BG == BG_DARK else "#f0f0f0"
        if hasattr(self, 'side_tabs'):
            self.side_tabs.configure(fg_color=tv_bg)
        if hasattr(self, 'tabs'):
            self.tabs.configure(fg_color=PANEL)
    
    # ------------------------------------------------------------------ dựng giao diện
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=470, corner_radius=0, fg_color=PANEL)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.pack_propagate(False)
        ctk.CTkLabel(sb, text="⚙  Cơ cấu phẳng n khâu", font=ctk.CTkFont(size=21, weight="bold"),
                     anchor="w").pack(fill="x", padx=16, pady=(16, 0))
        ctk.CTkLabel(sb, text="Vị trí  ·  Vận tốc  ·  Gia tốc  ·  Họa đồ", text_color=MUTED,
                     anchor="w").pack(fill="x", padx=16)
        self.preset_menu = ctk.CTkOptionMenu(sb, values=list(PRESETS), command=self.load_preset)
        self.preset_menu.pack(fill="x", padx=16, pady=(12, 4))
        
        # Nút chuyển đổi theme sáng/tối
        self.theme_btn = ctk.CTkButton(sb, text="☀️  Chuyển sang Theme Sáng", 
                                       command=self.toggle_theme,
                                       fg_color="#2a2f3b", hover_color="#39404f")
        self.theme_btn.pack(fill="x", padx=16, pady=(0, 12))

        # Màu nền tabview theo theme
        tv_bg = "#14161d" if BG == BG_DARK else "#f0f0f0"
        tv = self.side_tabs = ctk.CTkTabview(sb, fg_color=tv_bg)
        tv.pack(fill="both", expand=True, padx=10, pady=8)
        tv.add("Điều khiển")
        tv.add("Cơ cấu")

        t = tv.tab("Điều khiển")
        self.s_phi = ParamSlider(t, "φ₂ – góc khâu dẫn (độ)", 0, 360, 10, self.refresh)
        self.s_w = ParamSlider(t, "|ω₂| – vận tốc góc (rad/s)", 0, 100, 5, self.on_param)
        self.dir_w = ctk.CTkSegmentedButton(t, values=[CCW, CW], command=lambda _: self.on_param())
        self.dir_w.set(CW)
        self.s_e = ParamSlider(t, "|ε₂| – gia tốc góc (rad/s²)", 0, 500, 10, self.on_param)
        self.dir_e = ctk.CTkSegmentedButton(t, values=[CCW, CW], command=lambda _: self.on_param())
        self.dir_e.set(CW)
        self.s_phi.pack(fill="x", padx=6, pady=(6, 0))
        self.s_w.pack(fill="x", padx=6)
        self.dir_w.pack(fill="x", padx=6, pady=(0, 10))
        self.s_e.pack(fill="x", padx=6)
        self.dir_e.pack(fill="x", padx=6, pady=(0, 12))

        row = ctk.CTkFrame(t, fg_color="transparent")
        row.pack(fill="x", padx=6)
        self.play_btn = ctk.CTkButton(row, text="▶  Chạy", width=110, command=self.toggle_play)
        self.play_btn.pack(side="left")
        self.speed = ParamSlider(row, "Tốc độ (°/khung)", 0.2, 12, 2, lambda: None)
        self.speed.pack(side="left", fill="x", expand=True, padx=(12, 0))

        self.sw_v = ctk.CTkSwitch(t, text="Vector vận tốc trên lược đồ", command=self.refresh)
        self.sw_a = ctk.CTkSwitch(t, text="Vector gia tốc trên lược đồ", command=self.refresh)
        self.sw_l = ctk.CTkSwitch(t, text="Hiện tên điểm", command=self.refresh)
        self.sw_l.select()
        for s in (self.sw_v, self.sw_a, self.sw_l):
            s.pack(anchor="w", padx=10, pady=3)

        b = ctk.CTkFrame(t, fg_color="transparent")
        b.pack(fill="x", padx=6, pady=(14, 0))
        # Màu nút xuất theo theme
        btn_color = "#2a2f3b" if BG == BG_DARK else "#e0e0e0"
        btn_hover = "#39404f" if BG == BG_DARK else "#d0d0d0"
        ctk.CTkButton(b, text="Xuất ảnh PNG", fg_color=btn_color, hover_color=btn_hover, command=self.export_png).pack(side="left", expand=True, fill="x",
                                                                           padx=(0, 4))
        ctk.CTkButton(b, text="Xuất báo cáo TXT", fg_color=btn_color, hover_color=btn_hover, command=self.export_txt).pack(side="left", expand=True,
                                                                               fill="x", padx=(4, 0))

        t = tv.tab("Cơ cấu")
        scroll = ctk.CTkScrollableFrame(t, fg_color="transparent")
        scroll.pack(fill="both", expand=True)
        ctk.CTkLabel(scroll, text="Điểm  (cố định / tự do: x, y  ·  tay quay: tên tâm, r)", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x")
        self.t_points = TableEditor(scroll, [("name", "Tên", 56, None), ("kind", "Loại", 100, list(KIND_EN)),
                                             ("a", "x / tâm", 70, None), ("b", "y / r", 70, None)], height=150)
        self.t_points.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(scroll, text="Thanh  (điểm i – điểm j, độ dài L)", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x")
        self.t_bars = TableEditor(scroll, [("i", "i", 56, None), ("j", "j", 56, None), ("L", "L (m)", 80, None)],
                                  height=110)
        self.t_bars.pack(fill="x", pady=(2, 10))
        ctk.CTkLabel(scroll, text="Điểm gắn trên khâu  (s dọc i→j, t vuông góc)", anchor="w",
                     font=ctk.CTkFont(weight="bold")).pack(fill="x")
        self.t_locals = TableEditor(scroll, [("name", "Tên", 50, None), ("i", "i", 44, None), ("j", "j", 44, None),
                                             ("s", "s (m)", 62, None), ("t", "t (m)", 62, None)], height=100)
        self.t_locals.pack(fill="x", pady=(2, 10))
        ctk.CTkButton(scroll, text="✔  Áp dụng cơ cấu", fg_color="#1f8f6a", hover_color="#27b085",
                      command=self.apply_mechanism).pack(fill="x", pady=(2, 4))
        f = ctk.CTkFrame(scroll, fg_color="transparent")
        f.pack(fill="x")
        # Màu nút theo theme
        btn_color = "#2a2f3b" if BG == BG_DARK else "#e0e0e0"
        btn_hover = "#39404f" if BG == BG_DARK else "#d0d0d0"
        ctk.CTkButton(f, text="Lưu JSON", fg_color=btn_color, hover_color=btn_hover, command=self.save_json).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(f, text="Mở JSON", fg_color=btn_color, hover_color=btn_hover, command=self.load_json).pack(
            side="left", expand=True, fill="x", padx=(4, 0))
        self.msg = ctk.CTkLabel(scroll, text="", wraplength=390, justify="left", anchor="w")
        self.msg.pack(fill="x", pady=6)

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=BG)
        main.grid(row=0, column=1, sticky="nsew", padx=(8, 10), pady=10)
        self.status = ctk.CTkLabel(main, text="", anchor="w", font=ctk.CTkFont(size=13))
        self.status.pack(side="bottom", fill="x", padx=8, pady=(4, 0))
        self.tabs = ctk.CTkTabview(main, fg_color=PANEL, command=self.redraw)
        self.tabs.pack(fill="both", expand=True)
        for name in (T1, T2, T3):
            self.tabs.add(name)

        self.fig = Figure(figsize=(9, 6), dpi=100, facecolor=BG)
        gs = self.fig.add_gridspec(2, 2, width_ratios=[1.35, 1], left=0.05, right=0.985, top=0.945, bottom=0.07,
                                   wspace=0.16, hspace=0.32)
        self.ax_m = self.fig.add_subplot(gs[:, 0])
        self.ax_v = self.fig.add_subplot(gs[0, 1])
        self.ax_a = self.fig.add_subplot(gs[1, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tabs.tab(T1))
        self.canvas.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        top = ctk.CTkFrame(self.tabs.tab(T2), fg_color="transparent")
        top.pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(top, text="Đại lượng:").pack(side="left", padx=(6, 8))
        self.q_menu = ctk.CTkOptionMenu(top, values=["—"], width=260, command=lambda _: self.redraw())
        self.q_menu.pack(side="left")
        self.fig2 = Figure(figsize=(9, 5), dpi=100, facecolor=BG)
        self.ax_c = self.fig2.add_subplot(111)
        self.fig2.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.12)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tabs.tab(T2))
        self.canvas2.get_tk_widget().configure(bg=BG, highlightthickness=0)
        self.canvas2.get_tk_widget().pack(fill="both", expand=True)

        # Màu nền textbox theo theme
        txt_bg = "#0f1116" if BG == BG_DARK else "#ffffff"
        self.txt = ctk.CTkTextbox(self.tabs.tab(T3), font=ctk.CTkFont(family="Consolas", size=13), wrap="none",
                                  fg_color=txt_bg)
        self.txt.pack(fill="both", expand=True)

    # ------------------------------------------------------------------ dữ liệu <-> giao diện
    def read_params(self):
        phi = math.radians(self.s_phi.get())
        w = self.s_w.get() * (1 if self.dir_w.get() == CCW else -1)
        e = self.s_e.get() * (1 if self.dir_e.get() == CCW else -1)
        return phi, w, e

    def populate(self, d):
        self.t_points.set_rows([{"name": p["name"], "kind": KIND_VI[p["kind"]], "a": fmt(p["a"]), "b": fmt(p["b"])}
                                for p in d["points"]])
        self.t_bars.set_rows([{"i": b["i"], "j": b["j"], "L": fmt(b["L"])} for b in d["bars"]])
        self.t_locals.set_rows([{k: fmt(q[k]) for k in ("name", "i", "j", "s", "t")} for q in d.get("locals", [])])
        self.s_phi.set(d["phi"])
        self.s_w.set(abs(d["w"]))
        self.dir_w.set(CCW if d["w"] >= 0 else CW)
        self.s_e.set(abs(d["e"]))
        self.dir_e.set(CCW if d["e"] >= 0 else CW)

    def collect(self):
        phi, w, e = self.read_params()
        return {
            "points": [{"name": r["name"].strip(), "kind": KIND_EN[r["kind"]], "a": r["a"].strip(),
                        "b": r["b"].strip()} for r in self.t_points.get_rows()],
            "bars": [{"i": r["i"].strip(), "j": r["j"].strip(), "L": r["L"].strip()} for r in self.t_bars.get_rows()],
            "locals": [{k: r[k].strip() for k in ("name", "i", "j", "s", "t")} for r in self.t_locals.get_rows()],
            "phi": math.degrees(phi), "w": w, "e": e,
        }

    def load_preset(self, name):
        self.preset_menu.set(name)
        self.populate(PRESETS[name])
        self.apply_mechanism()

    def apply_mechanism(self):
        try:
            mech = Mechanism(self.collect())
        except (ValueError, KeyError) as ex:
            self.msg.configure(text=f"⚠ {ex}", text_color=RED)
            return False
        phi, w, e = self.read_params()
        res, msg = mech.assemble(phi, w, e)
        if res is None:
            self.msg.configure(text=f"⚠ {msg}", text_color=RED)
            return False
        self.mech, self.res = mech, res
        self.qopts = quantity_options(mech)
        self.q_menu.configure(values=list(self.qopts))
        names = [i + j for i, j in mech.all_bars()]
        self.q_menu.set(f"ω  {names[1] if len(names) > 1 else names[0]}  (rad/s)")
        self.compute_sweep()
        self.msg.configure(text="✔ Đã áp dụng cơ cấu.\n" + "\n".join(mech.structure_report()[:3]),
                           text_color=GREEN)
        self.refresh()
        return True

    def compute_sweep(self):
        self._sweep_job = None
        if not self.mech:
            return
        phi, w, e = self.read_params()
        self.sweep_data = self.mech.sweep(phi, w, e)
        if self.sweep_data["results"]:
            self.view = view_from(self.sweep_data["results"])
        self.redraw()

    def on_param(self, *_):
        self.refresh()
        if self._sweep_job:
            self.after_cancel(self._sweep_job)
        self._sweep_job = self.after(400, self.compute_sweep)     # tính lại đồ thị khi ngừng kéo thanh trượt

    # ------------------------------------------------------------------ tính & vẽ
    def refresh(self, *_):
        if not self.mech:
            return False
        phi, w, e = self.read_params()
        res, msg = self.mech.solve(phi, w, e)
        if res is None:
            self.status.configure(text=f"⚠ {msg}", text_color=RED)
            return False
        self.res = res
        self.status.configure(text=f"✔ φ₂ = {math.degrees(phi) % 360:.1f}°  ·  cơ cấu lắp được", text_color=GREEN)
        self.redraw()
        return True

    def redraw(self, *_):
        if not (self.mech and self.res):
            return
        tab = self.tabs.get()
        if tab == T1:
            view = self.view or view_from([self.res])
            opts = dict(show_v=bool(self.sw_v.get()), show_a=bool(self.sw_a.get()), labels=bool(self.sw_l.get()))
            draw_mechanism(self.ax_m, self.mech, self.res, view, opts)
            draw_plan(self.ax_v, self.mech, self.res, "V", "Họa đồ vận tốc  (m/s)", "p")
            draw_plan(self.ax_a, self.mech, self.res, "A", "Họa đồ gia tốc  (m/s²)", "π")
            self.canvas.draw_idle()
        elif tab == T2:
            label = self.q_menu.get()
            key = self.qopts.get(label)
            if key:
                draw_curve(self.ax_c, self.sweep_data, key, label, math.degrees(self.res["phi"]),
                           get_quantity(self.res, key))
            self.canvas2.draw_idle()
        else:
            self.txt.delete("1.0", "end")
            self.txt.insert("1.0", report(self.mech, self.res))

    # ------------------------------------------------------------------ hoạt họa
    def toggle_play(self):
        self.playing = not self.playing
        self.play_btn.configure(text="⏸  Dừng" if self.playing else "▶  Chạy")
        if self.playing:
            self._tick()

    def _step(self):
        """Một bước hoạt họa: tăng φ₂; nếu không lắp được thì lùi lại và đổi chiều."""
        old = self.s_phi.get()
        self.s_phi.set((old + self.play_dir * self.speed.get()) % 360)
        if not self.refresh():
            self.s_phi.set(old)
            self.play_dir *= -1

    def _tick(self):
        if not self.playing:
            return
        self._step()
        self.after(30, self._tick)

    # ------------------------------------------------------------------ xuất / nhập
    def export_png(self):
        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path:
            self.fig.savefig(path, dpi=200, facecolor=BG)

    def export_txt(self):
        if not (self.mech and self.res):
            return
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(report(self.mech, self.res))

    def save_json(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.collect(), f, indent=2, ensure_ascii=False)

    def load_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if path:
            with open(path, encoding="utf-8") as f:
                self.populate(json.load(f))
            self.apply_mechanism()


if __name__ == "__main__":
    # Mặc định bắt đầu với theme tối
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    App().mainloop()
