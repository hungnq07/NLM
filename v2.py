#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ỨNG DỤNG CƠ CẤU 4 KHÂU BẢN LỀ - GIAO DIỆN DASHBOARD
====================================================

Mục đích
--------
File này gộp các chức năng của hai file cũ:
  * sang.py : nhập thông số, phân tích cấu trúc, vận tốc, gia tốc,
              vẽ lược đồ, mô phỏng chuyển động.
  * m.py    : nhập thông số theo bảng, vẽ họa đồ vectơ, lưu lịch sử,
              xuất ảnh + báo cáo TXT, giao diện hiện đại.

Điểm khác biệt của phiên bản này
--------------------------------
  1. Giao diện "dashboard" có theme tối/sáng, bố cục mới:
       - Thanh tiêu đề phía trên kèm nút chuyển theme.
       - Vùng kết quả lớn bên trái với các tab dạng nút viên thuốc.
       - Bảng nhập liệu cuộn được bên phải.
       - Thanh trạng thái phía dưới.
     (Không dùng Notebook như sang.py, không dùng 3 cột + tab Chrome như m.py.)
  2. TOÀN BỘ KẾT QUẢ ĐỀU Ở DẠNG CHỈ XEM:
       - Ô văn bản dùng tk.Text(state="disabled").
       - Bảng kết quả dùng ttk.Treeview(selectmode="none").
       - Các ô số liệu là tk.Label, không phải Entry.
     Người dùng vẫn có thể bôi đen và copy nhưng không sửa được nội dung.
  3. Có đầy đủ: preset PA1/PA2, chọn chiều ω₂/ε₂, phân tích cấu trúc,
     vận tốc, gia tốc, họa đồ vectơ, bật/tắt vectơ trên lược đồ, mô phỏng
     có quỹ đạo, lịch sử thông số, xuất PNG/PDF + TXT.

Cách chạy
---------
    python3 co_cau_4_khau_v3.py

Thư viện cần có: tkinter, numpy, matplotlib.

Quy ước dấu
-----------
  - Góc quay dương = NGƯỢC chiều kim đồng hồ (hệ trục Oxy, y hướng lên).
  - |ω₂|, |ε₂| là độ lớn; chiều do ô chọn "cùng"/"ngược" quyết định.
  - Mô phỏng quay theo đúng chiều ω₂ đã chọn.
"""

# ============================================================================
# 1. KHAI BÁO THƯ VIỆN
#    - os/json/datetime : lưu lịch sử, đặt tên file, ghi thời gian.
#    - tkinter          : giao diện desktop.
#    - numpy            : đại số vectơ, giải hệ phương trình tuyến tính.
#    - matplotlib       : vẽ lược đồ, họa đồ vận tốc/gia tốc, mô phỏng.
# ============================================================================
import os
import json
from datetime import datetime

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont

import numpy as np
import matplotlib

matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Arc, FancyArrowPatch, Circle
from matplotlib.lines import Line2D


# ============================================================================
# BẢN ĐỒ CODE THEO 5 PHẦN
#    Mỗi vùng dưới đây tương ứng một phần việc; không thay đổi thân hàm.
# ============================================================================
#   PHẦN 1 — Giao diện và nhập liệu
#   PHẦN 2 — Giải vị trí cơ cấu
#   PHẦN 3 — Giải vận tốc và gia tốc
#   PHẦN 4 — Vẽ hình và họa đồ
#   PHẦN 5 — Mô phỏng, báo cáo, lịch sử, xuất file
#   Lớp CoCauDashboard là vỏ chung, chứa method của Phần 1 và Phần 5.



# ============================================================================
# DÙNG CHUNG — BẢNG MÀU VÀ FONT
#    Các hằng số được cả 5 phần sử dụng.
# ============================================================================

DARK_THEME = dict(
    bg="#0b1120",
    header="#0f172a",
    card="#111c30",
    panel="#16233a",
    panel_alt="#1b2a44",
    border="#22314d",
    text="#e6edf7",
    muted="#8fa3bf",
    dim="#7c8ca5",
    accent="#38bdf8",
    accent_soft="#0e3a4f",
    success="#34d399",
    danger="#f87171",
    warning="#fbbf24",
    input="#0a1323",
    plot_bg="#0d1628",
    grid="#1f2d47",
    link2="#60a5fa",
    link3="#fb923c",
    link4="#34d399",
    force="#f97316",
    m3="#c084fc",
    m4="#f472b6",
    phi="#fbbf24",
)

# Theme sáng giữ đúng bộ khóa màu như theme tối. Hai cặp success/link4 và
# warning/phi cố ý dùng cùng giá trị để việc đổi màu widget theo giá trị cũ
# không bị nhập nhằng.
LIGHT_THEME = dict(
    bg="#eef2f7",
    header="#e2e8f0",
    card="#ffffff",
    panel="#f8fafc",
    panel_alt="#e8eef6",
    border="#cbd5e1",
    text="#0f172a",
    muted="#475569",
    dim="#64748b",
    accent="#0369a1",
    accent_soft="#dbeafe",
    success="#0f9d58",
    danger="#dc2626",
    warning="#b45309",
    input="#f4f7fb",
    plot_bg="#fbfdff",
    grid="#d7dde8",
    link2="#2563eb",
    link3="#ea580c",
    link4="#0f9d58",
    force="#b91c1c",
    m3="#7c3aed",
    m4="#db2777",
    phi="#b45309",
)

# PALETTE được cập nhật tại chỗ để mọi hàm vẽ/widget đang dùng luôn thấy theme mới.
PALETTE = dict(DARK_THEME)
THEME_IS_DARK = True

FONT = "TkDefaultFont"
MONO = "TkFixedFont"


# ============================================================================
# PHẦN 1 — GIAO DIỆN VÀ NHẬP LIỆU
#    Theme, preset, trường nhập, widget chỉ xem và các hàm dựng giao diện.
# ============================================================================

def set_theme(dark):
    """Cập nhật bảng màu hiện hành và trạng thái theme."""
    global THEME_IS_DARK
    THEME_IS_DARK = bool(dark)
    PALETTE.update(DARK_THEME if THEME_IS_DARK else LIGHT_THEME)

PRESETS = {
    "PA1": dict(
        L2=5.0, L3=4.5, lBM=2.0, lME=1.0, L4=6.0, L1=3.0,
        phi2=10.0, omega2=5.0, omega2_dir="cùng",
        eps2=10.0, eps2_dir="cùng",
        P3=210.0, alpha=10.0, M3=30.0, M4=150.0,
        m3=2.0, Js3=2.5, m4=1.0,
    ),
    "PA2": dict(
        L2=5.0, L3=4.0, lBM=2.5, lME=1.5, L4=6.0, L1=3.0,
        phi2=20.0, omega2=5.0, omega2_dir="cùng",
        eps2=20.0, eps2_dir="ngược",
        P3=240.0, alpha=20.0, M3=60.0, M4=200.0,
        m3=3.0, Js3=3.0, m4=2.0,
    ),
}

# Danh sách trường số và nhãn hiển thị. Thứ tự này cũng dùng khi ghi báo cáo.
FIELDS = [
    ("L2", "L₂ = lAB  (m)"),
    ("L3", "L₃ = lBC  (m)"),
    ("lBM", "lBM  (m)"),
    ("lME", "lME  (m)"),
    ("L4", "L₄ = lCD  (m)"),
    ("L1", "L₁ = lAD  (m)"),
    ("phi2", "Góc vị trí φ₂  (độ)"),
    ("omega2", "|ω₂|  (rad/s)"),
    ("eps2", "|ε₂|  (rad/s²)"),
    ("P3", "P₃  (N)"),
    ("alpha", "Góc α của P₃  (độ)"),
    ("M3", "M₃  (N·m)"),
    ("M4", "M₄  (N·m)"),
    ("m3", "m₃  (kg)"),
    ("Js3", "Jₛ₃  (kg·m²)"),
    ("m4", "m₄  (kg)"),
]
LABELS = dict(FIELDS)

# Hai trường chiều quay dùng Combobox thay vì Entry số.
DIR_FIELDS = [
    ("omega2_dir", "Chiều ω₂ (cùng / ngược kim đồng hồ)"),
    ("eps2_dir", "Chiều ε₂ (cùng / ngược kim đồng hồ)"),
]
LABELS.update(dict(DIR_FIELDS))

def pick_font(candidates, fallback):
    """Chọn font đầu tiên có sẵn trên hệ thống, tránh lỗi hiển thị chữ."""
    available = set(tkfont.families())
    for name in candidates:
        if name in available:
            return name
    return fallback

class ReadOnlyText(tk.Frame):
    """Ô văn bản chỉ xem. Chỉ nội bộ lớp được phép cập nhật nội dung."""

    def __init__(self, master, height=10, font=None, **kwargs):
        super().__init__(master, bg=PALETTE["card"], **kwargs)
        self.text = tk.Text(
            self, height=height, width=1, wrap="word",
            bg=PALETTE["plot_bg"], fg=PALETTE["text"],
            insertbackground=PALETTE["text"],
            selectbackground=PALETTE["accent_soft"],
            selectforeground=PALETTE["text"],
            relief="flat", bd=0, padx=12, pady=10,
            font=font or (MONO, 10), state="disabled",
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            highlightcolor=PALETTE["border"],
        )
        scroll = ttk.Scrollbar(self, orient="vertical",
                               style="Dark.Vertical.TScrollbar",
                               command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

    def set_text(self, content):
        """Cập nhật nội dung nhưng giữ nguyên trạng thái chỉ xem."""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")
        self.text.yview_moveto(0.0)


class ReadOnlyTable(tk.Frame):
    """Bảng kết quả chỉ xem dùng Treeview, không cho chỉnh sửa ô."""

    def __init__(self, master, columns, height=5, **kwargs):
        super().__init__(master, bg=PALETTE["panel"], **kwargs)
        self.columns = columns
        self.tree = ttk.Treeview(
            self, columns=[c[0] for c in columns], show="headings",
            height=height, selectmode="none", style="Dark.Treeview",
        )
        for key, title, width, anchor in columns:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor, stretch=True)
        self.tree.tag_configure("odd", background=PALETTE["panel_alt"])
        self.tree.tag_configure("even", background=PALETTE["panel"])
        self.tree.pack(fill="both", expand=True)

    def apply_theme(self):
        """Cập nhật màu nền xen kẽ của Treeview sau khi đổi theme."""
        self.configure(bg=PALETTE["panel"])
        self.tree.tag_configure("odd", background=PALETTE["panel_alt"])
        self.tree.tag_configure("even", background=PALETTE["panel"])

    def set_rows(self, rows):
        """Xóa dữ liệu cũ, nạp lại danh sách hàng và tô màu xen kẽ."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        for i, row in enumerate(rows):
            self.tree.insert("", "end", values=row,
                             tags=("odd" if i % 2 else "even",))


class MetricCard(tk.Frame):
    """Thẻ hiển thị một đại lượng lớn (ω3, ω4, ε3, ε4) - chỉ xem."""

    def __init__(self, master, title, **kwargs):
        super().__init__(master, bg=PALETTE["panel"],
                         highlightthickness=1,
                         highlightbackground=PALETTE["border"], **kwargs)
        tk.Label(self, text=title, bg=PALETTE["panel"], fg=PALETTE["muted"],
                 font=(FONT, 9), anchor="w").pack(
            anchor="w", padx=12, pady=(9, 0))
        self.value = tk.Label(self, text="—", bg=PALETTE["panel"],
                              fg=PALETTE["accent"], font=(MONO, 14, "bold"),
                              anchor="w")
        self.value.pack(anchor="w", padx=12)
        self.direction = tk.Label(self, text="", bg=PALETTE["panel"],
                                  fg=PALETTE["text"], font=(FONT, 9),
                                  anchor="w", justify="left", wraplength=170)
        self.direction.pack(anchor="w", padx=12, pady=(0, 9))

    def set(self, value_text, direction_text):
        """Cập nhật số liệu; không tạo Entry nên người dùng không sửa được."""
        self.value.config(text=value_text)
        self.direction.config(text=direction_text)


# ============================================================================
# PHẦN 2 — GIẢI VỊ TRÍ CƠ CẤU
#    Dựng A, B, C, D, M, E từ chiều dài khâu và góc phi2.
# ============================================================================

def circle_intersect(p0, r0, p1, r1, branch=1):
    """
    Giao hai đường tròn (p0, r0) và (p1, r1).
    Dùng để xác định khớp C từ hai khâu BC và CD.
    branch=1 luôn chọn nghiệm s1, branch=-1 chọn nghiệm s2.
    Giữ cố định nhánh lắp ráp để C không nhảy cấu hình đối xứng.
    Trả về None nếu hai đường tròn không cắt nhau.
    """
    p0 = np.array(p0, dtype=float)
    p1 = np.array(p1, dtype=float)
    d = np.linalg.norm(p1 - p0)
    if d < 1e-9 or d > r0 + r1 or d < abs(r0 - r1):
        return None

    a = (r0 ** 2 - r1 ** 2 + d ** 2) / (2.0 * d)
    h = np.sqrt(max(r0 ** 2 - a ** 2, 0.0))
    p2 = p0 + a * (p1 - p0) / d
    ux, uy = (p1 - p0) / d
    s1 = np.array([p2[0] + h * uy, p2[1] - h * ux])
    s2 = np.array([p2[0] - h * uy, p2[1] + h * ux])
    return s1 if branch == 1 else s2


def solve_positions(p):
    """
    Giải vị trí toàn bộ cơ cấu tại góc φ₂ cho trước.
    Trả về dict tọa độ A, B, C, D, M, E.
    Ném ValueError nếu bộ kích thước không khép được vòng B-C-D.
    """
    A = np.array([0.0, 0.0])
    D = np.array([p["L1"], 0.0])
    phi2 = np.radians(p["phi2"])
    B = A + p["L2"] * np.array([np.cos(phi2), np.sin(phi2)])

    C = circle_intersect(B, p["L3"], D, p["L4"], branch=1)
    if C is None:
        raise ValueError(
            "Không dựng được cơ cấu với bộ thông số này "
            "(vòng kín B-C-D không tồn tại). Hãy kiểm tra L1, L2, L3, L4 và φ₂."
        )

    # M nằm trên BC theo tỉ lệ lBM/lBC; E nằm trên đường vuông góc với BC tại M.
    BC = np.linalg.norm(C - B)
    u = (C - B) / BC
    M = B + (p["lBM"] / BC) * (C - B)
    E = M + p["lME"] * np.array([u[1], -u[0]])

    return dict(A=A, B=B, C=C, D=D, M=M, E=E)


# ============================================================================
# PHẦN 3 — GIẢI VẬN TỐC VÀ GIA TỐC
#    Quy ước dấu, vectơ phụ trợ và nghiệm omega3, omega4, eps3, eps4.
# ============================================================================

def perp(v):
    """Quay vectơ v thêm +90°: tương đương phép nhân ω × r với ω = 1."""
    return np.array([-v[1], v[0]], dtype=float)


def vec_polar(v):
    """Trả về (độ lớn, góc phương so với Ox) của một vectơ 2D."""
    mag = float(np.linalg.norm(v))
    if mag < 1e-9:
        return mag, None
    ang = float(np.degrees(np.arctan2(v[1], v[0])) % 360.0)
    return mag, ang


def rot_text(value, symbol="ω"):
    """Mô tả chiều quay của một đại lượng góc có dấu (CCW dương)."""
    if abs(value) < 1e-9:
        if symbol == "ω":
            return "đứng yên (ω = 0)"
        return f"bằng 0 ({symbol} = 0)"
    return "↺ ngược chiều kim đồng hồ" if value > 0 else "↻ cùng chiều kim đồng hồ"


def signed_w2(p):
    """Trả về ω₂ có dấu theo quy ước CCW dương (nguồn quy ước duy nhất)."""
    return -p["omega2"] if p["omega2_dir"] == "cùng" else p["omega2"]


def signed_e2(p):
    """Trả về ε₂ có dấu theo quy ước CCW dương (nguồn quy ước duy nhất)."""
    return -p["eps2"] if p["eps2_dir"] == "cùng" else p["eps2"]


def sign_of(value, tol=1e-12):
    """Dấu của một đại lượng: -1, 0 hoặc +1."""
    if abs(value) < tol:
        return 0
    return 1 if value > 0 else -1

def solve_velocities(p, pts):
    """
    Giải vận tốc bằng phương trình vectơ:
        vB = ω₂ × AB
        vC = vB + ω₃ × BC = vD + ω₄ × DC   (vD = 0)
        vM, vE suy ra từ khâu 3 cứng.
    """
    A, B, C, D, M, E = (pts[k] for k in "ABCDME")

    # Chiều "cùng kim" là âm, "ngược kim" là dương theo quy ước CCW dương.
    w2 = signed_w2(p)
    vB = w2 * perp(B - A)

    # Hệ 2 phương trình cho ω3, ω4. Ma trận suy biến khi BC // CD.
    mat = np.column_stack([perp(C - B), -perp(C - D)])
    if abs(np.linalg.det(mat)) < 1e-9:
        raise ValueError(
            "BC // CD (vị trí đặc biệt): không xác định được ω₃, ω₄."
        )
    w3, w4 = np.linalg.solve(mat, -vB)

    vC = w4 * perp(C - D)
    vM = vB + w3 * perp(M - B)
    vE = vB + w3 * perp(E - B)

    return dict(
        w2=float(w2), w3=float(w3), w4=float(w4),
        B=vB, C=vC, M=vM, E=vE,
    )


def solve_accelerations(p, pts, vel):
    """
    Giải gia tốc bằng:
        aB = ε₂ × AB − ω₂²·AB
        aC = aB + ε₃ × BC − ω₃²·BC = aD + ε₄ × DC − ω₄²·DC
        aM, aE suy ra từ khâu 3 cứng.
    """
    A, B, C, D, M, E = (pts[k] for k in "ABCDME")
    w2, w3, w4 = vel["w2"], vel["w3"], vel["w4"]

    e2 = signed_e2(p)
    aB = e2 * perp(B - A) - (w2 ** 2) * (B - A)

    mat = np.column_stack([perp(C - B), -perp(C - D)])
    if abs(np.linalg.det(mat)) < 1e-9:
        raise ValueError(
            "BC // CD (vị trí đặc biệt): không xác định được ε₃, ε₄."
        )
    rhs = -aB + (w3 ** 2) * (C - B) - (w4 ** 2) * (C - D)
    e3, e4 = np.linalg.solve(mat, rhs)

    aC = e4 * perp(C - D) - (w4 ** 2) * (C - D)
    aM = aB + e3 * perp(M - B) - (w3 ** 2) * (M - B)
    aE = aB + e3 * perp(E - B) - (w3 ** 2) * (E - B)

    return dict(
        e2=float(e2), e3=float(e3), e4=float(e4),
        B=aB, C=aC, M=aM, E=aE,
    )


# ============================================================================
# PHẦN 4 — VẼ HÌNH VÀ HỌA ĐỒ
#    Lược đồ cơ cấu, lực, mô men, kích thước và đa giác vectơ.
# ============================================================================

def style_axes(ax, show_ticks=True):
    """Trang trí trục theo theme tối."""
    ax.set_facecolor(PALETTE["plot_bg"])
    ax.grid(True, ls=":", lw=0.7, color=PALETTE["grid"], alpha=0.85)
    if show_ticks:
        ax.tick_params(labelsize=8, colors=PALETTE["muted"])
        for spine in ax.spines.values():
            spine.set_color(PALETTE["border"])
    else:
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        for spine in ax.spines.values():
            spine.set_visible(False)


def draw_mechanism(ax, pts, p, trails=None, title=None,
                   vel=None, acc=None, show_v=False, show_a=False):
    """
    Vẽ lược đồ cơ cấu.
    trails: dict các danh sách tọa độ B, C, M, E để vẽ quỹ đạo (chế độ mô phỏng).
    vel/acc: kết quả động học dùng để vẽ thêm vectơ khi show_v/show_a bật.
    """
    ax.clear()
    ax.set_facecolor(PALETTE["plot_bg"])
    A, B, C, D, M, E = (pts[k] for k in "ABCDME")

    # --- Giá cố định: đường AD và các ký hiệu gạch chéo tại A, D ---
    ax.plot([A[0], D[0]], [A[1], D[1]], "--", color=PALETTE["muted"],
            lw=1.0, alpha=0.7, zorder=1)
    for pt in (A, D):
        for k in range(-3, 4):
            ax.plot(
                [pt[0] - 0.15 + 0.05 * k, pt[0] - 0.28 + 0.05 * k],
                [pt[1] - 0.05, pt[1] - 0.30],
                color=PALETTE["muted"], lw=0.8, alpha=0.8, zorder=1,
            )
        ax.plot([pt[0] - 0.35, pt[0] + 0.35], [pt[1] - 0.05] * 2,
                color=PALETTE["muted"], lw=1.4, zorder=1)

    # --- Quỹ đạo (nếu có) ---
    if trails:
        for key, color in (("B", PALETTE["link2"]), ("C", PALETTE["link4"]),
                           ("M", PALETTE["m3"]), ("E", PALETTE["force"])):
            arr = np.array(trails.get(key, []))
            if len(arr) > 1:
                ax.plot(arr[:, 0], arr[:, 1], ls="--", lw=1.0,
                        color=color, alpha=0.45, zorder=1)

    # --- Các khâu ---
    ax.plot(*zip(A, B), color=PALETTE["link2"], lw=4.5,
            solid_capstyle="round", zorder=3)
    ax.plot(*zip(B, C), color=PALETTE["link3"], lw=4.5,
            solid_capstyle="round", zorder=3)
    ax.plot(*zip(C, D), color=PALETTE["link4"], lw=4.5,
            solid_capstyle="round", zorder=3)
    ax.plot(*zip(M, E), "--", color=PALETTE["muted"], lw=1.2,
            alpha=0.9, zorder=3)

    # --- Ký hiệu vuông góc tại M ---
    u = (C - B) / np.linalg.norm(C - B)
    n = np.array([u[1], -u[0]])
    s = 0.12
    ax.plot(*zip(M + s * u, M + s * u + s * n, M + s * n),
            color=PALETTE["muted"], lw=0.9, zorder=3)

    # --- Khớp bản lề A, B, C, D ---
    for pt, name, off in ((A, "A", (-16, -18)), (B, "B", (8, 6)),
                          (C, "C", (8, 6)), (D, "D", (8, -16))):
        ax.add_patch(Circle(pt, 0.085, facecolor=PALETTE["plot_bg"],
                            edgecolor=PALETTE["text"], lw=2, zorder=5))
        ax.annotate(name, pt, textcoords="offset points", xytext=off,
                    fontsize=11, fontweight="bold", color=PALETTE["text"], zorder=6)

    # --- Điểm M và E ---
    ax.plot(*M, "o", color=PALETTE["text"], ms=4, zorder=5)
    ax.plot(*E, "o", color=PALETTE["text"], ms=5, zorder=5)
    ax.annotate(r"$M\equiv S_3$", M, textcoords="offset points",
                xytext=(8, 8), fontsize=9, fontweight="bold",
                color=PALETTE["text"], zorder=6)
    ax.annotate("E", E, textcoords="offset points", xytext=(7, -15),
                fontsize=10, fontweight="bold", color=PALETTE["text"], zorder=6)

    # --- Góc φ2 ---
    ang = np.degrees(np.arctan2(B[1] - A[1], B[0] - A[0])) % 360.0
    rad = 0.65
    ax.add_patch(Arc(A, 2 * rad, 2 * rad, theta1=0, theta2=ang,
                     color=PALETTE["phi"], lw=1.5, zorder=3))
    mid = np.radians(ang / 2)
    ax.annotate(r"$\varphi_2$", A + rad * 1.35 * np.array([np.cos(mid), np.sin(mid)]),
                color=PALETTE["phi"], fontsize=11, zorder=6)

    # --- Chiều quay của ω2 và ε2 (tham khảo hmi_v2.py: rot_arrow) ---
    # Cung đi ngược chiều kim đồng hồ khi dấu dương, cùng chiều khi dấu âm.
    def rot_arrow(center, radius, sign, color, label,
                  centre_deg=135.0, half=28.0):
        if sign == 0:
            return
        t = np.radians(np.linspace(centre_deg - half,
                                   centre_deg + half, 40))
        if sign < 0:
            t = t[::-1]
        xs = center[0] + radius * np.cos(t)
        ys = center[1] + radius * np.sin(t)
        ax.plot(xs[:-2], ys[:-2], color=color, lw=1.8, zorder=4)
        ax.add_patch(FancyArrowPatch(
            (xs[-3], ys[-3]), (xs[-1], ys[-1]),
            arrowstyle="-|>", mutation_scale=13, color=color, lw=1.8,
            shrinkA=0, shrinkB=0, zorder=5,
        ))
        tm = np.radians(centre_deg)
        ax.annotate(
            label,
            (center[0] + 1.18 * radius * np.cos(tm),
             center[1] + 1.18 * radius * np.sin(tm)),
            color=color, fontsize=10, fontweight="bold",
            ha="center", va="center", zorder=6,
        )

    # Lấy dấu từ kết quả đã giải (như hmi_v2), fallback về quy ước đầu vào.
    w2_arc = vel["w2"] if vel is not None else signed_w2(p)
    e2_arc = acc["e2"] if acc is not None else signed_e2(p)
    rot_arrow(A, 0.95, sign_of(w2_arc),
              PALETTE["accent"], r"$\omega_2$")
    rot_arrow(A, 1.28, sign_of(e2_arc),
              PALETTE["m4"], r"$\varepsilon_2$")

    # --- Lực P3 tại E ---
    al = np.radians(p["alpha"])
    tip = E + 1.1 * np.array([np.cos(al), np.sin(al)])
    ax.plot([E[0], E[0] + 1.3], [E[1]] * 2, ":", color=PALETTE["force"],
            lw=1.0, alpha=0.7, zorder=2)
    ax.add_patch(FancyArrowPatch(E, tip, color=PALETTE["force"], lw=2.4,
                                 arrowstyle="-|>", mutation_scale=16, zorder=5))
    ax.annotate(r"$P_3$", tip, textcoords="offset points", xytext=(7, 4),
                color=PALETTE["force"], fontsize=11, fontweight="bold", zorder=6)
    ax.annotate(r"$\alpha$", E + 0.75 * np.array([1, 0]),
                textcoords="offset points", xytext=(0, -14),
                color=PALETTE["force"], fontsize=10, zorder=6)

    # --- Mô men M3, M4 (cung tròn có mũi tên) ---
    def moment_arc(center, radius, label, color, value, label_off=(-30, 0)):
        sign = sign_of(value)
        ax.add_patch(Arc(center, 2 * radius, 2 * radius, theta1=30, theta2=300,
                         color=color, lw=1.8, zorder=3))
        if sign:
            theta = 300.0 if sign > 0 else 30.0
            t = np.radians(theta)
            tip = center + radius * np.array([np.cos(t), np.sin(t)])
            tangent = np.array([-np.sin(t), np.cos(t)])
            if sign < 0:
                tangent = -tangent
            ax.add_patch(FancyArrowPatch(
                tip - 0.08 * tangent, tip,
                color=color, lw=1.8, arrowstyle="-|>",
                mutation_scale=11, zorder=3,
            ))
        ax.annotate(label, center, textcoords="offset points", xytext=label_off,
                    color=color, fontsize=11, fontweight="bold", zorder=6)

    c3 = M + 0.55 * np.array([-1, 0.3])
    c4 = (C + D) / 2 + 0.5 * np.array([0.6, 0.2])
    moment_arc(c3, 0.32, r"$M_3$", PALETTE["m3"], p["M3"])
    moment_arc(c4, 0.32, r"$M_4$", PALETTE["m4"], p["M4"], (12, 0))

    # --- Nhãn kích thước các khâu ---
    def dim_label(P1, P2, name, value, off=(0, 7)):
        ax.annotate(rf"$l_{{{name}}}$ = {value:.2f}", (P1 + P2) / 2,
                    textcoords="offset points", xytext=off, fontsize=8,
                    ha="center", color=PALETTE["dim"], family=MONO)

    dim_label(A, B, "AB", p["L2"])
    dim_label(B, C, "BC", p["L3"], (-28, 12))
    dim_label(C, D, "CD", p["L4"], (-32, 0))
    dim_label(A, D, "AD", p["L1"], (0, -24))

    # --- Vectơ vận tốc/gia tốc tại các điểm (tùy chọn) ---
    def vector_arrows(data, symbol, color, enabled):
        """Vẽ các vectơ cùng một tỉ lệ để so sánh tương đối."""
        if not enabled or not data:
            return []
        vectors = [(name, np.asarray(data[name], dtype=float))
                   for name in "BCME" if name in data]
        magnitudes = [np.linalg.norm(v) for _name, v in vectors]
        max_mag = max(magnitudes, default=0.0)
        if max_mag < 1e-9:
            return []

        geometry = np.array([A, B, C, D, M, E])
        span = max(float(np.ptp(geometry, axis=0).max()), 1.0)
        scale = (0.16 * span) / max_mag
        tips = []
        for name, vector in vectors:
            if np.linalg.norm(vector) < 1e-9:
                continue
            start = pts[name]
            end = start + scale * vector
            ax.add_patch(FancyArrowPatch(
                start, end, arrowstyle="-|>", mutation_scale=12,
                color=color, lw=2.0, shrinkA=0, shrinkB=0,
                alpha=0.95, zorder=7,
            ))
            ax.annotate(
                rf"${symbol}_{{{name}}}$", end, xytext=(5, 5),
                textcoords="offset points", color=color, fontsize=9,
                fontweight="bold", zorder=8,
            )
            tips.append(end)
        return tips

    vector_tips = vector_arrows(vel, "v", PALETTE["accent"], show_v)
    vector_tips += vector_arrows(acc, "a", PALETTE["m4"], show_a)

    # --- Giới hạn trục và trang trí ---
    all_pts = [A, B, C, D, M, E, tip, c3, c4] + vector_tips
    xs = [q[0] for q in all_pts]
    ys = [q[1] for q in all_pts]
    ax.set_xlim(min(xs) - 1.5, max(xs) + 1.7)
    ax.set_ylim(min(ys) - 1.5, max(ys) + 1.2)
    ax.set_aspect("equal", adjustable="box")
    style_axes(ax, show_ticks=False)
    if title:
        ax.set_title(title, fontsize=10, color=PALETTE["text"],
                     fontweight="bold", pad=8)


def draw_vector_polygon(ax, data, symbol, title, pole, suffix, pole_tex):
    """
    Vẽ họa đồ vectơ vận tốc hoặc gia tốc.
    data chứa các vectơ B, C, M, E; gốc họa đồ là 0.
    """
    ax.clear()
    ax.set_facecolor(PALETTE["plot_bg"])
    origin = np.zeros(2)
    b, c, m, e = data["B"], data["C"], data["M"], data["E"]

    def arrow(p0, p1, color, lw=2.0, ls="-"):
        if np.linalg.norm(p1 - p0) < 1e-9:
            return
        ax.add_patch(FancyArrowPatch(
            p0, p1, color=color, lw=lw, arrowstyle="-|>",
            mutation_scale=12, linestyle=ls, zorder=3,
            shrinkA=0, shrinkB=0,
        ))

    # Các vectơ chính và vectơ nối (b→c, m→e).
    arrow(origin, b, PALETTE["link2"])
    arrow(origin, c, PALETTE["link4"])
    arrow(b, c, PALETTE["link3"])
    arrow(origin, m, PALETTE["m3"], lw=1.6)
    arrow(origin, e, PALETTE["force"], lw=1.6)
    arrow(m, e, PALETTE["muted"], lw=1.2, ls="--")

    # Điểm cực và nhãn các đầu mút.
    ax.plot(*origin, "o", color=PALETTE["text"], ms=5, zorder=4)
    ax.annotate(pole_tex, origin, textcoords="offset points", xytext=(-8, -18),
                fontsize=10, fontweight="bold", color=PALETTE["text"],
                ha="right", zorder=5)
    for pt, name, off in ((b, "b", (-12, 7)), (c, "c", (8, 7)),
                          (m, "m", (8, -15)), (e, "e", (8, 7))):
        ax.plot(*pt, "o", color=PALETTE["text"], ms=4, zorder=4)
        ax.annotate(name + suffix, pt, textcoords="offset points", xytext=off,
                    fontsize=11, fontweight="bold",
                    color=PALETTE["text"], zorder=5)

    # Chú thích màu.
    def vtex(sub):
        return r"$\vec{" + symbol + r"}_{" + sub + r"}$"

    handles = [
        Line2D([0], [0], color=PALETTE["link2"], lw=2, label=f"{vtex('B')} = {pole}b{suffix}"),
        Line2D([0], [0], color=PALETTE["link4"], lw=2, label=f"{vtex('C')} = {pole}c{suffix}"),
        Line2D([0], [0], color=PALETTE["link3"], lw=2, label=f"{vtex('CB')} = b{suffix}c{suffix}"),
        Line2D([0], [0], color=PALETTE["m3"], lw=2, label=f"{vtex('M')} = {pole}m{suffix}"),
        Line2D([0], [0], color=PALETTE["force"], lw=2, label=f"{vtex('E')} = {pole}e{suffix}"),
        Line2D([0], [0], color=PALETTE["muted"], lw=1.4, ls="--",
               label=f"{vtex('EM')} = m{suffix}e{suffix}"),
    ]
    legend = ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.08),
                       ncol=3, fontsize=8, frameon=False)
    for txt in legend.get_texts():
        txt.set_color(PALETTE["muted"])

    # Giới hạn trục có lề để nhãn không bị cắt.
    all_pts = np.array([origin, b, c, m, e])
    lo, hi = all_pts.min(axis=0), all_pts.max(axis=0)
    span = max(hi[0] - lo[0], hi[1] - lo[1])
    if span < 1e-6:
        span = 1.0
        lo, hi = lo - 0.5, hi + 0.5
    margin = 0.20 * span
    ax.set_xlim(lo[0] - margin, hi[0] + margin)
    ax.set_ylim(lo[1] - margin, hi[1] + margin)
    ax.set_aspect("equal", adjustable="box")
    style_axes(ax, show_ticks=True)
    ax.set_title(title, fontsize=10, color=PALETTE["text"],
                 fontweight="bold", pad=8)


def draw_velocity_polygon(ax, vel):
    """Họa đồ vận tốc với điểm cực p."""
    draw_vector_polygon(ax, vel, "v", "Họa đồ vận tốc (m/s)",
                        "p", "", r"$p\equiv a\equiv d$")


def draw_accel_polygon(ax, acc):
    """Họa đồ gia tốc với điểm cực π."""
    draw_vector_polygon(ax, acc, "a", "Họa đồ gia tốc (m/s²)",
                        "π", "'", r"$\pi\equiv a\equiv d$")


def show_figure_message(fig, ax, canvas, message):
    """Hiển thị thông báo giữa một figure trống (khi lỗi hoặc chưa có kết quả)."""
    ax.clear()
    ax.set_facecolor(PALETTE["plot_bg"])
    ax.text(0.5, 0.5, message, ha="center", va="center",
            transform=ax.transAxes, color=PALETTE["muted"],
            fontsize=10, wrap=True)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    canvas.draw_idle()


# ============================================================================
# PHẦN 5 — MÔ PHỎNG, BÁO CÁO, LỊCH SỬ, XUẤT FILE
#    Sinh văn bản, đọc/ghi lịch sử và các hàm điều phối kết quả.
# ============================================================================

# File lịch sử riêng để không ảnh hưởng file lịch sử của m.py.
HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "lich_su_co_cau_v3.json"
)
HISTORY_MAX = 50

def structure_numbers():
    """Số khâu động n, số khớp loại 5 p5, loại 4 p4 và bậc tự do W."""
    n, p5, p4 = 3, 4, 0
    return n, p5, p4, 3 * n - 2 * p5 - p4


def structure_text(p):
    """Phân tích cấu trúc + tóm tắt thông số đầu vào."""
    n, p5, p4, W = structure_numbers()
    chieu = {"cùng": "cùng chiều kim đồng hồ", "ngược": "ngược chiều kim đồng hồ"}
    return (
        "PHÂN TÍCH CẤU TRÚC CƠ CẤU\n"
        + "=" * 56 + "\n"
        f"• Số khâu động: n = {n}  (khâu 2: AB, khâu 3: BC, khâu 4: CD)\n"
        f"• Số khớp loại 5: p5 = {p5}  (A, B, C, D);  p4 = {p4}\n"
        f"• Bậc tự do: W = 3n − 2p5 − p4 = 3·{n} − 2·{p5} − {p4} = {W}\n\n"
        "TÁCH NHÓM ASSUR\n"
        + "-" * 56 + "\n"
        "• Khâu dẫn là khâu 2 (AB), nối giá bằng khớp quay tại A\n"
        "  → cơ cấu loại I (hạng 1).\n"
        "• Khâu 3 (BC) và khâu 4 (CD) nối nhau và nối giá qua B, C, D\n"
        "  (dạng RRR). Bậc tự do nhóm: Wn = 3·2 − 2·3 = 0\n"
        "  → nhóm tĩnh định hợp lệ.\n\n"
        "XẾP LOẠI CƠ CẤU\n"
        + "-" * 56 + "\n"
        "Cơ cấu = 1 khâu dẫn loại I ghép nối tiếp 1 nhóm tĩnh định loại 2.\n"
        "→ CƠ CẤU LOẠI 2 (HẠNG II).\n\n"
        "THÔNG SỐ ĐỘNG HỌC / LỰC ĐÃ NHẬP\n"
        + "-" * 56 + "\n"
        f"• L1 = {p['L1']:g} m;  L2 = {p['L2']:g} m;  L3 = {p['L3']:g} m;  "
        f"L4 = {p['L4']:g} m\n"
        f"• lBM = {p['lBM']:g} m;  lME = {p['lME']:g} m;  φ2 = {p['phi2']:g}°\n"
        f"• |ω2| = {abs(p['omega2']):g} rad/s ({chieu[p['omega2_dir']]})\n"
        f"• |ε2| = {abs(p['eps2']):g} rad/s² ({chieu[p['eps2_dir']]})\n"
        f"• P3 = {p['P3']:g} N, α = {p['alpha']:g}°, M3 = {p['M3']:g} N·m, "
        f"M4 = {p['M4']:g} N·m\n"
        f"• m3 = {p['m3']:g} kg, Js3 = {p['Js3']:g} kg·m², m4 = {p['m4']:g} kg\n"
    )


def vector_table_rows(data, prefix):
    """Tạo dữ liệu hàng cho bảng Treeview vận tốc/gia tốc."""
    rows = []
    for name in "BCME":
        v = data[name]
        mag, ang = vec_polar(v)
        rows.append((
            f"{prefix}{name}",
            f"{v[0]:.3f}",
            f"{v[1]:.3f}",
            f"{mag:.3f}",
            "—" if ang is None else f"{ang:.1f}°",
        ))
    return rows


def vector_table_text(data, prefix, unit):
    """Bảng dạng văn bản (dùng trong báo cáo TXT)."""
    lines = [
        f"{'Điểm':<7}{'x':>10}{'y':>10}{'Độ lớn':>12}{'Hướng':>12}",
        "-" * 53,
    ]
    for name in "BCME":
        v = data[name]
        mag, ang = vec_polar(v)
        a = f"{ang:.1f}°" if ang is not None else "—"
        lines.append(
            f"{prefix + name:<7}{v[0]:>10.3f}{v[1]:>10.3f}{mag:>12.3f}{a:>12}"
        )
    lines.append(f"(đơn vị: {unit}; hướng đo từ Ox, ngược chiều kim đồng hồ)")
    return "\n".join(lines)


def velocity_text(p, vel):
    """Toàn bộ kết quả bài toán vận tốc dạng văn bản."""
    return (
        "PHÂN TÍCH VẬN TỐC\n"
        + "=" * 56 + "\n"
        "Phương trình:\n"
        "  vB = ω₂ × AB\n"
        "  vC = vB + ω₃ × BC = vD + ω₄ × DC   (vD = 0)\n"
        "  vM = vB + ω₃ × BM,  vE = vB + ω₃ × BE\n\n"
        f"• ω2 = {abs(vel['w2']):.4f} rad/s  ({rot_text(vel['w2'])})\n"
        f"• ω3 = {abs(vel['w3']):.4f} rad/s  ({rot_text(vel['w3'])})\n"
        f"• ω4 = {abs(vel['w4']):.4f} rad/s  ({rot_text(vel['w4'])})\n\n"
        + vector_table_text(vel, "v", "m/s")
        + "\n\nGhi chú: họa đồ vẽ đúng phương, chiều và tỉ lệ tương đối;\n"
          "gốc họa đồ p trùng gốc tọa độ.\n"
    )


def accel_text(p, acc):
    """Toàn bộ kết quả bài toán gia tốc dạng văn bản."""
    return (
        "PHÂN TÍCH GIA TỐC\n"
        + "=" * 56 + "\n"
        "Phương trình:\n"
        "  aB = ε₂ × AB − ω₂²·AB\n"
        "  aC = aB + ε₃ × BC − ω₃²·BC = aD + ε₄ × DC − ω₄²·DC   (aD = 0)\n"
        "  aM = aB + ε₃ × BM − ω₃²·BM,  aE = aB + ε₃ × BE − ω₃²·BE\n\n"
        f"• ε2 = {abs(acc['e2']):.4f} rad/s²  ({rot_text(acc['e2'], 'ε')})\n"
        f"• ε3 = {abs(acc['e3']):.4f} rad/s²  ({rot_text(acc['e3'], 'ε')})\n"
        f"• ε4 = {abs(acc['e4']):.4f} rad/s²  ({rot_text(acc['e4'], 'ε')})\n\n"
        + vector_table_text(acc, "a", "m/s²")
        + "\n"
    )


def full_report(p, pts, vel, acc, err_vel=None, err_acc=None):
    """Ghép báo cáo hoàn chỉnh: thời gian, thông số, cấu trúc, vận tốc, gia tốc."""
    lines = [
        "BÁO CÁO CƠ CẤU 4 KHÂU BẢN LỀ",
        "Thời gian: " + datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "=" * 64,
        "THÔNG SỐ ĐẦU VÀO",
        "-" * 64,
    ]
    for key, label in FIELDS:
        lines.append(f"{label:<36}= {p[key]:g}")
    for key, label in DIR_FIELDS:
        lines.append(f"{label:<36}= {p[key]}")
    lines += [
        "",
        "TỌA ĐỘ CÁC ĐIỂM (m)",
        "-" * 64,
    ]
    for name in "ABCDME":
        q = pts[name]
        lines.append(f"{name:<4}= ( {q[0]:10.4f} ; {q[1]:10.4f} )")
    lines += ["", "=" * 64, structure_text(p), "=" * 64]
    lines.append(
        velocity_text(p, vel) if vel is not None
        else "PHÂN TÍCH VẬN TỐC\n" + "=" * 56 + "\n" + (err_vel or "Không xác định.")
    )
    lines.append("=" * 64)
    lines.append(
        accel_text(p, acc) if acc is not None
        else "PHÂN TÍCH GIA TỐC\n" + "=" * 56 + "\n" + (err_acc or "Không xác định.")
    )
    return "\n".join(lines)

def load_history():
    """Đọc lịch sử từ file; bỏ qua mọi bản ghi không hợp lệ."""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [h for h in data if isinstance(h, dict) and "params" in h]
    except (OSError, ValueError):
        pass
    return []


def save_history(history):
    """Ghi lịch sử ra file JSON; lỗi ghi file không làm hỏng ứng dụng."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def history_label(item):
    """Chuỗi ngắn hiển thị trong Listbox lịch sử."""
    p = item["params"]
    return (f"{item.get('time', '')}  φ₂={p.get('phi2', 0):g}°  "
            f"L₂={p.get('L2', 0):g} L₃={p.get('L3', 0):g} "
            f"L₄={p.get('L4', 0):g} L₁={p.get('L1', 0):g}")


# ============================================================================
# LỚP ỨNG DỤNG — VỎ CHUNG CỦA PHẦN 1 VÀ PHẦN 5
#    Method giao diện/nhập liệu nằm ở Phần 1; method điều phối/mô phỏng/xuất file nằm ở Phần 5.
# ============================================================================

class CoCauDashboard(tk.Tk):
    # ==========================================================================
    # PHẦN 1 — CÁC METHOD GIAO DIỆN VÀ NHẬP LIỆU
    # ==========================================================================
    def __init__(self):
        super().__init__()
        self.title("Cơ cấu 4 khâu bản lề · Dashboard chỉ xem kết quả")
        self.geometry("1520x920")
        self.minsize(1240, 760)
        self.configure(bg=PALETTE["bg"])

        # Chọn font phù hợp với máy đang chạy.
        global FONT, MONO
        FONT = pick_font(
            ["Segoe UI", "Inter", "Noto Sans", "IBM Plex Sans",
             "DejaVu Sans", "Arial"], "TkDefaultFont")
        MONO = pick_font(
            ["Consolas", "JetBrains Mono", "IBM Plex Mono",
             "DejaVu Sans Mono", "Menlo", "Courier New"], "TkFixedFont")

        # Trạng thái dữ liệu và kết quả gần nhất.
        self.vars = {}
        self.dir_vars = {}
        self.last_params = None
        self.last_pts = None
        self.last_vel = None
        self.last_acc = None
        self.last_err_vel = None
        self.last_err_acc = None
        self.last_report = ""
        self.history = load_history()

        # Trạng thái mô phỏng.
        self.sim_phi = 0.0
        self.sim_running = False
        self.sim_after = None
        self.trails = {"B": [], "C": [], "M": [], "E": []}
        self.sim_speed_var = tk.DoubleVar(value=2.0)
        self.sim_phi_var = tk.DoubleVar(value=0.0)
        self.ve_quy_dao_var = tk.BooleanVar(value=True)
        self.show_vel_var = tk.BooleanVar(value=False)
        self.show_acc_var = tk.BooleanVar(value=False)
        self.is_dark_theme = THEME_IS_DARK

        # Xây dựng giao diện theo thứ tự: style → header → body → statusbar.
        self._setup_style()
        self._build_header()
        self._build_body()
        self._build_statusbar()

        # Nạp dữ liệu khởi tạo: lịch sử gần nhất nếu có, ngược lại dùng PA1.
        self._refresh_history_list()
        if self.history:
            self._fill_form(self.history[0]["params"])
        else:
            self._fill_form(PRESETS["PA1"])
        self.on_compute(silent=True)

    # ------------------------------------------------------------------
    # 10.1. STYLE
    # ------------------------------------------------------------------
    def _setup_style(self):
        """Cấu hình lại toàn bộ widget ttk theo bảng màu đang dùng."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # Danh sách xổ xuống của Combobox là Listbox nội bộ, cần đặt qua option DB.
        self.option_add("*TCombobox*Listbox.background", PALETTE["input"])
        self.option_add("*TCombobox*Listbox.foreground", PALETTE["text"])
        self.option_add("*TCombobox*Listbox.selectBackground",
                        PALETTE["accent_soft"])
        self.option_add("*TCombobox*Listbox.selectForeground",
                        PALETTE["accent"])

        # Combobox nền theo theme, chữ tương phản.
        style.configure(
            "Dark.TCombobox",
            fieldbackground=PALETTE["input"], background=PALETTE["input"],
            foreground=PALETTE["text"], arrowcolor=PALETTE["accent"],
            bordercolor=PALETTE["border"], lightcolor=PALETTE["input"],
            darkcolor=PALETTE["input"], padding=5, font=(FONT, 10),
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", PALETTE["input"])],
            foreground=[("readonly", PALETTE["text"])],
            selectbackground=[("readonly", PALETTE["input"])],
            selectforeground=[("readonly", PALETTE["text"])],
        )

        # Thanh cuộn dọc.
        style.configure(
            "Dark.Vertical.TScrollbar",
            background=PALETTE["panel_alt"], troughcolor=PALETTE["card"],
            bordercolor=PALETTE["card"], arrowcolor=PALETTE["muted"],
            lightcolor=PALETTE["panel_alt"], darkcolor=PALETTE["panel_alt"],
        )
        style.map("Dark.Vertical.TScrollbar",
                  background=[("active", PALETTE["accent_soft"])])

        # Bảng Treeview chỉ đọc.
        style.configure(
            "Dark.Treeview",
            background=PALETTE["panel"], fieldbackground=PALETTE["panel"],
            foreground=PALETTE["text"], rowheight=27, borderwidth=0,
            font=(MONO, 9),
        )
        style.configure(
            "Dark.Treeview.Heading",
            background=PALETTE["panel_alt"], foreground=PALETTE["muted"],
            relief="flat", font=(FONT, 9, "bold"), padding=(6, 6),
        )
        style.map("Dark.Treeview.Heading",
                  background=[("active", PALETTE["panel_alt"])])

        # Thanh trượt góc/tốc độ mô phỏng.
        style.configure(
            "Sim.Horizontal.TScale",
            background=PALETTE["card"], troughcolor=PALETTE["input"],
            bordercolor=PALETTE["border"], lightcolor=PALETTE["accent"],
            darkcolor=PALETTE["accent"], sliderlength=22,
        )

    # ------------------------------------------------------------------
    # 10.2. CHUYỂN THEME SÁNG / TỐI
    # ------------------------------------------------------------------
    def _theme_color_map(self, target):
        """Ánh xạ từng màu cũ sang màu mới theo cùng khóa trong PALETTE."""
        return {value.lower(): target[key] for key, value in PALETTE.items()}

    def _retint_widget_tree(self, widget, mapping):
        """Đổi màu mọi widget con dựa trên giá trị màu palette cũ."""
        options = (
            "background", "foreground", "activebackground", "activeforeground",
            "selectbackground", "selectforeground", "highlightbackground",
            "highlightcolor", "insertbackground", "disabledforeground",
            "selectcolor", "troughcolor",
        )
        for option in options:
            try:
                value = widget.cget(option)
            except (tk.TclError, AttributeError):
                continue
            replacement = mapping.get(str(value).lower())
            if replacement:
                try:
                    widget.configure(**{option: replacement})
                except tk.TclError:
                    pass

        # Canvas tự vẽ icon header nên phải đổi màu từng item.
        if isinstance(widget, tk.Canvas):
            for item in widget.find_all():
                for option in ("fill", "outline"):
                    try:
                        value = widget.itemcget(item, option)
                    except tk.TclError:
                        continue
                    replacement = mapping.get(str(value).lower())
                    if replacement:
                        try:
                            widget.itemconfigure(item, **{option: replacement})
                        except tk.TclError:
                            pass

        for child in widget.winfo_children():
            self._retint_widget_tree(child, mapping)

    def toggle_theme(self):
        """Chuyển đổi giao diện tối/sáng, kể cả widget, bảng và matplotlib."""
        new_dark = not self.is_dark_theme
        target = DARK_THEME if new_dark else LIGHT_THEME
        mapping = self._theme_color_map(target)

        self._retint_widget_tree(self, mapping)
        set_theme(new_dark)
        self.is_dark_theme = THEME_IS_DARK
        self.configure(bg=PALETTE["bg"])

        # ttk không đổi màu theo widget.configure nên phải cấu hình lại style.
        self._setup_style()
        for table in (self.tbl_vel, self.tbl_acc):
            table.apply_theme()

        self.theme_btn.configure(
            text="☀  NỀN SÁNG" if self.is_dark_theme else "☾  NỀN TỐI")
        self._redraw_theme_figures()
        self.set_status(
            "Đã chuyển sang giao diện sáng." if not self.is_dark_theme
            else "Đã chuyển sang giao diện tối.", "info")

    def _redraw_theme_figures(self):
        """Vẽ lại các hình theo bảng màu mới mà không tính lại thông số."""
        for fig in (self.fig_struct, self.fig_vel, self.fig_acc, self.fig_sim):
            fig.set_facecolor(PALETTE["plot_bg"])

        if self.last_params is not None and self.last_pts is not None:
            self._draw_structure_mechanism()

            if self.last_vel is not None:
                draw_velocity_polygon(self.ax_vel, self.last_vel)
            else:
                show_figure_message(
                    self.fig_vel, self.ax_vel, self.canvas_vel,
                    self.last_err_vel or "Chưa có họa đồ vận tốc")

            if self.last_acc is not None:
                draw_accel_polygon(self.ax_acc, self.last_acc)
            else:
                show_figure_message(
                    self.fig_acc, self.ax_acc, self.canvas_acc,
                    self.last_err_acc or "Chưa có họa đồ gia tốc")

            self._sim_draw()
        else:
            message = self.last_report or "Chưa có dữ liệu."
            show_figure_message(self.fig_struct, self.ax_struct,
                                self.canvas_struct, message)
            show_figure_message(self.fig_vel, self.ax_vel, self.canvas_vel,
                                "Chưa có họa đồ vận tốc")
            show_figure_message(self.fig_acc, self.ax_acc, self.canvas_acc,
                                "Chưa có họa đồ gia tốc")
            show_figure_message(self.fig_sim, self.ax_sim, self.canvas_sim,
                                message)

        self.canvas_struct.draw_idle()
        self.canvas_vel.draw_idle()
        self.canvas_acc.draw_idle()
        self.canvas_sim.draw_idle()

    # ------------------------------------------------------------------
    # 10.3. HEADER
    # ------------------------------------------------------------------
    def _build_header(self):
        """Thanh tiêu đề trên cùng với biểu tượng cơ cấu vẽ bằng Canvas."""
        header = tk.Frame(self, bg=PALETTE["header"])
        header.pack(fill="x")

        inner = tk.Frame(header, bg=PALETTE["header"])
        inner.pack(fill="x", padx=26, pady=14)

        icon = tk.Canvas(inner, width=58, height=52, bg=PALETTE["header"],
                         highlightthickness=0)
        icon.pack(side="left", padx=(0, 16))
        icon.create_line(10, 42, 24, 14, fill=PALETTE["accent"], width=3)
        icon.create_line(24, 14, 46, 20, fill=PALETTE["link3"], width=3)
        icon.create_line(46, 20, 38, 44, fill=PALETTE["link4"], width=3)
        icon.create_line(10, 42, 38, 44, fill=PALETTE["muted"], width=1)
        for x, y, col in ((10, 42, PALETTE["accent"]), (24, 14, PALETTE["link3"]),
                          (46, 20, PALETTE["link4"]), (38, 44, PALETTE["text"])):
            icon.create_oval(x - 4, y - 4, x + 4, y + 4,
                             fill=PALETTE["header"], outline=col, width=2)

        titles = tk.Frame(inner, bg=PALETTE["header"])
        titles.pack(side="left")
        tk.Label(titles, text="CƠ CẤU 4 KHÂU BẢN LỀ",
                 bg=PALETTE["header"], fg=PALETTE["text"],
                 font=(FONT, 19, "bold")).pack(anchor="w")
        tk.Label(titles,
                 text="Dashboard động học · cấu trúc · vận tốc · gia tốc · mô phỏng",
                 bg=PALETTE["header"], fg=PALETTE["muted"],
                 font=(FONT, 10)).pack(anchor="w")

        tk.Label(inner, text="KẾT QUẢ CHỈ XEM", bg=PALETTE["accent_soft"],
                 fg=PALETTE["accent"], font=(FONT, 9, "bold"),
                 padx=12, pady=6).pack(side="right")

        self.theme_btn = tk.Button(
            inner,
            text="☀  NỀN SÁNG" if self.is_dark_theme else "☾  NỀN TỐI",
            command=self.toggle_theme,
            bg=PALETTE["panel_alt"], fg=PALETTE["text"],
            activebackground=PALETTE["accent_soft"],
            activeforeground=PALETTE["accent"],
            relief="flat", bd=0, padx=12, pady=6,
            font=(FONT, 9, "bold"), cursor="hand2",
        )
        self.theme_btn.pack(side="right", padx=(0, 10))

    # ------------------------------------------------------------------
    # 10.4. THÂN CHÍNH
    # ------------------------------------------------------------------
    def _build_body(self):
        """Chia thân cửa sổ thành vùng kết quả (trái) và bảng nhập liệu (phải)."""
        body = tk.Frame(self, bg=PALETTE["bg"])
        body.pack(fill="both", expand=True, padx=16, pady=14)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        self._build_results_area(body)
        self._build_input_panel(body)

    # ------------------------------------------------------------------
    # 10.5. VÙNG KẾT QUẢ + CÁC TRANG
    # ------------------------------------------------------------------
    def _build_results_area(self, parent):
        """
        Vùng bên trái gồm:
          - hàng nút tab dạng viên thuốc (không dùng Notebook);
          - 5 trang xếp chồng, dùng tkraise để chuyển trang.
        """
        area = tk.Frame(parent, bg=PALETTE["bg"])
        area.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        area.rowconfigure(1, weight=1)
        area.columnconfigure(0, weight=1)

        # --- Hàng tab ---
        tabbar = tk.Frame(area, bg=PALETTE["bg"])
        tabbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.tab_buttons = {}
        self.pages = {}
        self.active_tab = "struct"
        tabs = [
            ("struct", "CẤU TRÚC"),
            ("vel", "VẬN TỐC"),
            ("acc", "GIA TỐC"),
            ("sim", "MÔ PHỎNG"),
            ("report", "BÁO CÁO"),
        ]
        for key, title in tabs:
            btn = tk.Button(
                tabbar, text=title, command=lambda k=key: self.show_tab(k),
                bg=PALETTE["card"], fg=PALETTE["muted"],
                activebackground=PALETTE["accent_soft"],
                activeforeground=PALETTE["accent"],
                relief="flat", bd=0, padx=16, pady=8,
                font=(FONT, 10, "bold"), cursor="hand2",
                highlightthickness=0,
            )
            btn.pack(side="left", padx=(0, 7))
            self.tab_buttons[key] = btn

        tk.Label(tabbar, text="Nội dung kết quả không thể chỉnh sửa",
                 bg=PALETTE["bg"], fg=PALETTE["dim"],
                 font=(FONT, 9)).pack(side="right")

        # --- Khung chứa các trang ---
        holder = tk.Frame(area, bg=PALETTE["bg"])
        holder.grid(row=1, column=0, sticky="nsew")
        holder.rowconfigure(0, weight=1)
        holder.columnconfigure(0, weight=1)

        self.pages["struct"] = self._page_structure(holder)
        self.pages["vel"] = self._page_velocity(holder)
        self.pages["acc"] = self._page_acceleration(holder)
        self.pages["sim"] = self._page_simulation(holder)
        self.pages["report"] = self._page_report(holder)

        # Tất cả trang nằm cùng ô grid; trang được chọn sẽ nổi lên trên.
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")
        self.show_tab("struct")

    def _card(self, parent, **kwargs):
        """Tạo khung 'card' có viền mảnh, dùng lại nhiều nơi."""
        return tk.Frame(parent, bg=PALETTE["card"], highlightthickness=1,
                        highlightbackground=PALETTE["border"], **kwargs)

    def _card_header(self, parent, title, badge=None):
        """Tạo phần tiêu đề của một card, có thể kèm nhãn nhỏ bên phải."""
        bar = tk.Frame(parent, bg=PALETTE["card"])
        bar.pack(fill="x", padx=16, pady=(13, 6))
        tk.Label(bar, text=title, bg=PALETTE["card"], fg=PALETTE["text"],
                 font=(FONT, 11, "bold")).pack(side="left")
        if badge:
            tk.Label(bar, text=badge, bg=PALETTE["accent_soft"],
                     fg=PALETTE["accent"], font=(FONT, 8, "bold"),
                     padx=8, pady=3).pack(side="right")
        return bar

    def _figure_canvas(self, parent, figsize=(5.2, 4.4), bg=None):
        """Tạo Figure + Canvas và trả về (figure, axes, canvas)."""
        bg = bg or PALETTE["plot_bg"]
        fig = Figure(figsize=figsize, facecolor=bg)
        fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        widget = canvas.get_tk_widget()
        widget.configure(bg=bg, highlightthickness=0)
        widget.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        return fig, ax, canvas

    # ---------- Trang 1: Cấu trúc ----------
    def _page_structure(self, holder):
        page = tk.Frame(holder, bg=PALETTE["bg"])
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=3, minsize=480)
        page.columnconfigure(1, weight=2, minsize=340)

        left = self._card(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_header(left, "LƯỢC ĐỒ CƠ CẤU", "HÌNH VẼ")
        self.fig_struct, self.ax_struct, self.canvas_struct = \
            self._figure_canvas(left)

        right = self._card(page)
        right.grid(row=0, column=1, sticky="nsew")
        self._card_header(right, "PHÂN TÍCH CẤU TRÚC", "CHỈ XEM")
        self.txt_struct = ReadOnlyText(right, height=12, font=(MONO, 10))
        self.txt_struct.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return page

    # ---------- Trang 2: Vận tốc ----------
    def _page_velocity(self, holder):
        page = tk.Frame(holder, bg=PALETTE["bg"])
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=3, minsize=480)
        page.columnconfigure(1, weight=2, minsize=340)

        left = self._card(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_header(left, "HỌA ĐỒ VẬN TỐC", "HÌNH VẼ")
        self.fig_vel, self.ax_vel, self.canvas_vel = self._figure_canvas(left)

        right = tk.Frame(page, bg=PALETTE["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        # Hai thẻ số liệu ω3, ω4.
        metrics = tk.Frame(right, bg=PALETTE["bg"])
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        metrics.columnconfigure(0, weight=1, uniform="m")
        metrics.columnconfigure(1, weight=1, uniform="m")
        self.card_w3 = MetricCard(metrics, "VẬN TỐC GÓC KHÂU 3 (ω₃)")
        self.card_w3.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.card_w4 = MetricCard(metrics, "VẬN TỐC GÓC KHÂU 4 (ω₄)")
        self.card_w4.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        # Bảng vận tốc các điểm.
        table_card = self._card(right)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self._card_header(table_card, "VẬN TỐC CÁC ĐIỂM", "CHỈ XEM")
        self.tbl_vel = ReadOnlyTable(
            table_card,
            columns=[
                ("diem", "Điểm", 56, "center"),
                ("x", "x (m/s)", 80, "e"),
                ("y", "y (m/s)", 80, "e"),
                ("mag", "Độ lớn", 80, "e"),
                ("ang", "Hướng", 72, "center"),
            ],
            height=4,
        )
        self.tbl_vel.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Ghi chú/công thức chỉ xem.
        note_card = self._card(right)
        note_card.grid(row=2, column=0, sticky="nsew")
        self._card_header(note_card, "GHI CHÚ", "CHỈ XEM")
        self.txt_vel_note = ReadOnlyText(note_card, height=6, font=(MONO, 9))
        self.txt_vel_note.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return page

    # ---------- Trang 3: Gia tốc ----------
    def _page_acceleration(self, holder):
        page = tk.Frame(holder, bg=PALETTE["bg"])
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=3, minsize=480)
        page.columnconfigure(1, weight=2, minsize=340)

        left = self._card(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_header(left, "HỌA ĐỒ GIA TỐC", "HÌNH VẼ")
        self.fig_acc, self.ax_acc, self.canvas_acc = self._figure_canvas(left)

        right = tk.Frame(page, bg=PALETTE["bg"])
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)
        right.columnconfigure(0, weight=1)

        metrics = tk.Frame(right, bg=PALETTE["bg"])
        metrics.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        metrics.columnconfigure(0, weight=1, uniform="m")
        metrics.columnconfigure(1, weight=1, uniform="m")
        self.card_e3 = MetricCard(metrics, "GIA TỐC GÓC KHÂU 3 (ε₃)")
        self.card_e3.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.card_e4 = MetricCard(metrics, "GIA TỐC GÓC KHÂU 4 (ε₄)")
        self.card_e4.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        table_card = self._card(right)
        table_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        self._card_header(table_card, "GIA TỐC CÁC ĐIỂM", "CHỈ XEM")
        self.tbl_acc = ReadOnlyTable(
            table_card,
            columns=[
                ("diem", "Điểm", 56, "center"),
                ("x", "x (m/s²)", 80, "e"),
                ("y", "y (m/s²)", 80, "e"),
                ("mag", "Độ lớn", 80, "e"),
                ("ang", "Hướng", 72, "center"),
            ],
            height=4,
        )
        self.tbl_acc.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        note_card = self._card(right)
        note_card.grid(row=2, column=0, sticky="nsew")
        self._card_header(note_card, "GHI CHÚ", "CHỈ XEM")
        self.txt_acc_note = ReadOnlyText(note_card, height=6, font=(MONO, 9))
        self.txt_acc_note.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return page

    # ---------- Trang 4: Mô phỏng ----------
    def _page_simulation(self, holder):
        page = tk.Frame(holder, bg=PALETTE["bg"])
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1, minsize=480)
        page.columnconfigure(1, weight=0, minsize=330)

        left = self._card(page)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self._card_header(left, "MÔ PHỎNG CHUYỂN ĐỘNG", "HOẠT ẢNH")
        self.fig_sim, self.ax_sim, self.canvas_sim = self._figure_canvas(
            left, figsize=(5.4, 4.8))

        # Bảng điều khiển mô phỏng bên phải.
        ctrl = self._card(page, width=330)
        ctrl.grid(row=0, column=1, sticky="ns")
        ctrl.grid_propagate(False)
        ctrl.pack_propagate(False)
        self._card_header(ctrl, "ĐIỀU KHIỂN", "THỜI GIAN THỰC")

        box = tk.Frame(ctrl, bg=PALETTE["card"])
        box.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # Nút chạy/tạm dừng và đặt lại.
        row = tk.Frame(box, bg=PALETTE["card"])
        row.pack(fill="x", pady=(4, 10))
        self.btn_run = tk.Button(
            row, text="▶  CHẠY", command=self.toggle_run,
            bg=PALETTE["accent"], fg=PALETTE["bg"],
            activebackground=PALETTE["accent"],
            activeforeground=PALETTE["bg"],
            relief="flat", bd=0, pady=8,
            font=(FONT, 10, "bold"), cursor="hand2",
        )
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 4))
        tk.Button(
            row, text="⟲  ĐẶT LẠI", command=self.reset_simulation,
            bg=PALETTE["panel_alt"], fg=PALETTE["text"],
            activebackground=PALETTE["border"],
            activeforeground=PALETTE["text"],
            relief="flat", bd=0, pady=8,
            font=(FONT, 10, "bold"), cursor="hand2",
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))

        # Thanh trượt tốc độ quay.
        tk.Label(box, text="Tốc độ quay (độ / khung hình)",
                 bg=PALETTE["card"], fg=PALETTE["muted"],
                 font=(FONT, 9), anchor="w").pack(anchor="w", pady=(6, 0))
        ttk.Scale(box, from_=0.2, to=10.0, variable=self.sim_speed_var,
                  orient="horizontal",
                  style="Sim.Horizontal.TScale").pack(fill="x", pady=(2, 10))

        # Thanh trượt góc φ2.
        tk.Label(box, text="Góc φ₂ hiện tại (độ)",
                 bg=PALETTE["card"], fg=PALETTE["muted"],
                 font=(FONT, 9), anchor="w").pack(anchor="w")
        self.scale_phi = ttk.Scale(
            box, from_=0.0, to=360.0, variable=self.sim_phi_var,
            orient="horizontal", style="Sim.Horizontal.TScale",
            command=self.on_phi_scale,
        )
        self.scale_phi.pack(fill="x", pady=(2, 4))
        self.lbl_phi = tk.Label(box, text="φ₂ = 0.0°", bg=PALETTE["card"],
                                fg=PALETTE["accent"],
                                font=(MONO, 11, "bold"), anchor="w")
        self.lbl_phi.pack(anchor="w", pady=(0, 8))

        # Tùy chọn vẽ quỹ đạo.
        tk.Checkbutton(
            box, text="Vẽ quỹ đạo B, C, M, E",
            variable=self.ve_quy_dao_var,
            command=self.redraw_simulation,
            bg=PALETTE["card"], fg=PALETTE["text"],
            activebackground=PALETTE["card"],
            activeforeground=PALETTE["text"],
            selectcolor=PALETTE["input"], highlightthickness=0, bd=0,
            font=(FONT, 9), anchor="w",
        ).pack(anchor="w", pady=(2, 10))

        # Thông tin mô phỏng chỉ xem.
        tk.Label(box, text="THÔNG TIN HIỆN TẠI · CHỈ XEM",
                 bg=PALETTE["card"], fg=PALETTE["muted"],
                 font=(FONT, 8, "bold"), anchor="w").pack(anchor="w")
        self.txt_sim_info = ReadOnlyText(box, height=12, font=(MONO, 9))
        self.txt_sim_info.pack(fill="both", expand=True, pady=(3, 0))
        return page

    # ---------- Trang 5: Báo cáo ----------
    def _page_report(self, holder):
        page = tk.Frame(holder, bg=PALETTE["bg"])
        page.rowconfigure(1, weight=1)
        page.columnconfigure(0, weight=1)

        # Thanh công cụ nhỏ phía trên báo cáo.
        tools = tk.Frame(page, bg=PALETTE["bg"])
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(tools, text="BÁO CÁO TỔNG HỢP", bg=PALETTE["bg"],
                 fg=PALETTE["text"],
                 font=(FONT, 12, "bold")).pack(side="left")
        tk.Button(
            tools, text="⤓  XUẤT ẢNH + TXT", command=self.export_results,
            bg=PALETTE["accent"], fg=PALETTE["bg"],
            activebackground=PALETTE["accent"],
            activeforeground=PALETTE["bg"],
            relief="flat", bd=0, padx=14, pady=7,
            font=(FONT, 9, "bold"), cursor="hand2",
        ).pack(side="right")

        card = self._card(page)
        card.grid(row=1, column=0, sticky="nsew")
        self._card_header(card, "TOÀN BỘ KẾT QUẢ", "CHỈ XEM")
        self.txt_report = ReadOnlyText(card, height=20, font=(MONO, 10))
        self.txt_report.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        return page

    # ------------------------------------------------------------------
    # 10.6. BẢNG NHẬP LIỆU BÊN PHẢI
    # ------------------------------------------------------------------
    def _build_input_panel(self, parent):
        """
        Card bên phải gồm:
          - tiêu đề cố định;
          - vùng cuộn chứa các nhóm thông số, nút thao tác, lịch sử.
        """
        panel = self._card(parent, width=448)
        panel.grid(row=0, column=1, sticky="ns")
        panel.grid_propagate(False)
        panel.rowconfigure(1, weight=1)
        panel.columnconfigure(0, weight=1)

        head = tk.Frame(panel, bg=PALETTE["card"])
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(13, 8))
        tk.Label(head, text="BẢNG NHẬP LIỆU", bg=PALETTE["card"],
                 fg=PALETTE["text"],
                 font=(FONT, 11, "bold")).pack(side="left")
        tk.Label(head, text="KẾT QUẢ CHỈ XEM", bg=PALETTE["accent_soft"],
                 fg=PALETTE["accent"], font=(FONT, 8, "bold"),
                 padx=8, pady=3).pack(side="right")

        # Canvas + scrollbar để form nhập cuộn được khi cửa sổ thấp.
        canvas = tk.Canvas(panel, bg=PALETTE["card"], highlightthickness=0,
                           width=430)
        scroll = ttk.Scrollbar(panel, orient="vertical",
                               style="Dark.Vertical.TScrollbar",
                               command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.grid(row=1, column=1, sticky="ns")
        canvas.grid(row=1, column=0, sticky="nsew")

        inner = tk.Frame(canvas, bg=PALETTE["card"])
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))

        # Chỉ cuộn khi chuột nằm trong panel, tránh ảnh hưởng vùng khác.
        def on_wheel(event):
            delta = -1 if (getattr(event, "num", 0) == 4 or event.delta > 0) else 1
            canvas.yview_scroll(delta, "units")

        def bind_wheel(_event):
            canvas.bind_all("<MouseWheel>", on_wheel)
            canvas.bind_all("<Button-4>", on_wheel)
            canvas.bind_all("<Button-5>", on_wheel)

        def unbind_wheel(_event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)

        self._build_form(inner)

    def _section(self, parent, title, subtitle=None):
        """Tạo một nhóm nhập liệu có nền sáng hơn card."""
        box = tk.Frame(parent, bg=PALETTE["panel"], highlightthickness=1,
                       highlightbackground=PALETTE["border"])
        box.pack(fill="x", padx=12, pady=(0, 10))
        tk.Label(box, text=title, bg=PALETTE["panel"], fg=PALETTE["accent"],
                 font=(FONT, 9, "bold"), anchor="w").pack(
            fill="x", padx=12, pady=(10, 0))
        if subtitle:
            tk.Label(box, text=subtitle, bg=PALETTE["panel"],
                     fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
                     justify="left", wraplength=380).pack(
                fill="x", padx=12, pady=(2, 0))
        body = tk.Frame(box, bg=PALETTE["panel"])
        body.pack(fill="x", padx=12, pady=(7, 11))
        return body

    def _build_form(self, parent):
        """Dựng toàn bộ form: preset, 4 nhóm thông số, nút, lịch sử."""

        # --- Nạp nhanh phương án mẫu ---
        preset_row = tk.Frame(parent, bg=PALETTE["card"])
        preset_row.pack(fill="x", padx=12, pady=(2, 10))
        tk.Label(preset_row, text="Nạp nhanh:", bg=PALETTE["card"],
                 fg=PALETTE["muted"], font=(FONT, 9)).pack(side="left")
        for name in ("PA1", "PA2"):
            tk.Button(
                preset_row, text=name,
                command=lambda n=name: self.load_preset(n),
                bg=PALETTE["panel_alt"], fg=PALETTE["text"],
                activebackground=PALETTE["accent_soft"],
                activeforeground=PALETTE["accent"],
                relief="flat", bd=0, padx=13, pady=4,
                font=(FONT, 9, "bold"), cursor="hand2",
            ).pack(side="left", padx=(8, 0))

        # --- 1. Hình học ---
        g = self._section(parent, "1 · HÌNH HỌC CƠ CẤU")
        for i, (a, b) in enumerate((("L2", "L3"), ("lBM", "lME"), ("L4", "L1"))):
            self._field(g, a, i, 0)
            self._field(g, b, i, 1)
        self._field(g, "phi2", 3, 0, span=2)

        # --- 2. Động học khâu dẫn ---
        g = self._section(
            parent, "2 · ĐỘNG HỌC KHÂU DẪN",
            "Nhập độ lớn ω₂, ε₂ và chọn riêng chiều quay của chúng.")
        self._field(g, "omega2", 0, 0)
        self._combo(g, "omega2_dir", 0, 1)
        self._field(g, "eps2", 1, 0)
        self._combo(g, "eps2_dir", 1, 1)

        # Hai tùy chọn vectơ áp dụng cho cả lược đồ cấu trúc và màn mô phỏng.
        vec_opts = tk.Frame(g, bg=PALETTE["panel"])
        vec_opts.grid(row=4, column=0, columnspan=2, sticky="ew",
                      pady=(7, 0))
        for text, var in (
            ("Hiện vectơ vận tốc trên lược đồ", self.show_vel_var),
            ("Hiện vectơ gia tốc trên lược đồ", self.show_acc_var),
        ):
            tk.Checkbutton(
                vec_opts, text=text, variable=var,
                command=self._on_vector_toggle,
                bg=PALETTE["panel"], fg=PALETTE["text"],
                activebackground=PALETTE["panel"],
                activeforeground=PALETTE["accent"],
                selectcolor=PALETTE["input"], highlightthickness=0, bd=0,
                font=(FONT, 9), anchor="w",
            ).pack(anchor="w")

        # --- 3. Tải trọng ---
        g = self._section(parent, "3 · LỰC VÀ MÔ MEN")
        self._field(g, "P3", 0, 0)
        self._field(g, "alpha", 0, 1)
        self._field(g, "M3", 1, 0)
        self._field(g, "M4", 1, 1)

        # --- 4. Khối lượng, quán tính ---
        g = self._section(parent, "4 · KHỐI LƯỢNG & QUÁN TÍNH")
        self._field(g, "m3", 0, 0)
        self._field(g, "Js3", 0, 1)
        self._field(g, "m4", 1, 0)

        # --- Nút thao tác chính ---
        actions = tk.Frame(parent, bg=PALETTE["card"])
        actions.pack(fill="x", padx=12, pady=(0, 10))
        tk.Button(
            actions, text="▶  TÍNH TOÁN & PHÂN TÍCH",
            command=self.on_compute,
            bg=PALETTE["accent"], fg=PALETTE["bg"],
            activebackground=PALETTE["success"],
            activeforeground=PALETTE["bg"],
            relief="flat", bd=0, pady=10,
            font=(FONT, 10, "bold"), cursor="hand2",
        ).pack(fill="x")
        tk.Button(
            actions, text="⤓  LƯU KẾT QUẢ (ẢNH + TXT)",
            command=self.export_results,
            bg=PALETTE["panel"], fg=PALETTE["accent"],
            activebackground=PALETTE["accent_soft"],
            activeforeground=PALETTE["accent"],
            relief="flat", bd=0, pady=8,
            font=(FONT, 9, "bold"), cursor="hand2",
        ).pack(fill="x", pady=(6, 0))
        tk.Label(actions, text="Mẹo: nhấn Enter tại ô nhập để tính lại nhanh.",
                 bg=PALETTE["card"], fg=PALETTE["dim"], font=(FONT, 8),
                 anchor="w").pack(anchor="w", pady=(6, 0))

        # --- 5. Lịch sử ---
        hist = self._section(parent, "5 · LỊCH SỬ THÔNG SỐ",
                             "Nhấp đúp một dòng để nạp lại thông số.")
        list_frame = tk.Frame(hist, bg=PALETTE["panel"])
        list_frame.pack(fill="x")
        self.hist_lb = tk.Listbox(
            list_frame, height=6, font=(MONO, 8), activestyle="none",
            exportselection=False, relief="flat",
            bg=PALETTE["input"], fg=PALETTE["text"],
            selectbackground=PALETTE["accent_soft"],
            selectforeground=PALETTE["text"],
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
        )
        hsb = ttk.Scrollbar(list_frame, orient="vertical",
                            style="Dark.Vertical.TScrollbar",
                            command=self.hist_lb.yview)
        self.hist_lb.configure(yscrollcommand=hsb.set)
        hsb.pack(side="right", fill="y")
        self.hist_lb.pack(side="left", fill="x", expand=True)
        self.hist_lb.bind("<Double-Button-1>",
                          lambda _e: self.load_selected_history())

        btns = tk.Frame(hist, bg=PALETTE["panel"])
        btns.pack(fill="x", pady=(7, 0))
        for i in range(3):
            btns.columnconfigure(i, weight=1, uniform="h")
        for i, (text, fg, cmd) in enumerate((
            ("Nạp", PALETTE["accent"], self.load_selected_history),
            ("Xóa dòng", PALETTE["text"], self.delete_selected_history),
            ("Xóa hết", PALETTE["danger"], self.clear_history),
        )):
            tk.Button(
                btns, text=text, command=cmd,
                bg=PALETTE["panel_alt"], fg=fg,
                activebackground=PALETTE["border"], activeforeground=fg,
                relief="flat", bd=0, pady=5,
                font=(FONT, 8, "bold"), cursor="hand2",
            ).grid(row=0, column=i, sticky="ew",
                   padx=(0 if i == 0 else 4, 0))

        # Khoảng trống cuối form cho dễ nhìn.
        tk.Frame(parent, bg=PALETTE["card"], height=6).pack(fill="x")

    def _field(self, parent, key, row, col, span=1):
        """
        Tạo nhãn + ô Entry cho một trường số.
        Mọi ô đều gắn sự kiện Enter để tính toán nhanh.
        """
        parent.columnconfigure(col, weight=1, uniform="f")
        tk.Label(parent, text=LABELS[key], bg=PALETTE["panel"],
                 fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
                 justify="left", wraplength=170 * span).grid(
            row=row * 2, column=col, columnspan=span, sticky="w",
            padx=(0 if col == 0 else 6, 0), pady=(5, 2))
        var = tk.StringVar()
        self.vars[key] = var
        entry = tk.Entry(
            parent, textvariable=var, font=(MONO, 10),
            bg=PALETTE["input"], fg=PALETTE["text"],
            insertbackground=PALETTE["accent"], relief="flat",
            highlightthickness=1,
            highlightbackground=PALETTE["border"],
            highlightcolor=PALETTE["accent"],
        )
        entry.grid(row=row * 2 + 1, column=col, columnspan=span,
                   sticky="ew", padx=(0 if col == 0 else 6, 0), ipady=5)
        entry.bind("<Return>", lambda _e: self.on_compute())

    def _combo(self, parent, key, row, col):
        """Tạo Combobox chọn chiều quay (cùng/ngược kim đồng hồ)."""
        parent.columnconfigure(col, weight=1, uniform="f")
        tk.Label(parent, text=LABELS[key], bg=PALETTE["panel"],
                 fg=PALETTE["muted"], font=(FONT, 8), anchor="w",
                 justify="left", wraplength=170).grid(
            row=row * 2, column=col, sticky="w",
            padx=(0 if col == 0 else 6, 0), pady=(5, 2))
        var = tk.StringVar(value="cùng")
        self.dir_vars[key] = var
        combo = ttk.Combobox(
            parent, textvariable=var, state="readonly",
            values=["cùng", "ngược"], style="Dark.TCombobox",
        )
        combo.grid(row=row * 2 + 1, column=col, sticky="ew",
                   padx=(0 if col == 0 else 6, 0))

    # ------------------------------------------------------------------
    # 10.7. THANH TRẠNG THÁI
    # ------------------------------------------------------------------
    def _build_statusbar(self):
        """Thanh dưới cùng hiển thị trạng thái và quy ước dấu."""
        bar = tk.Frame(self, bg=PALETTE["header"], height=30)
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Sẵn sàng.")
        self.status_label = tk.Label(
            bar, textvariable=self.status_var, bg=PALETTE["header"],
            fg=PALETTE["success"], font=(FONT, 9), anchor="w",
        )
        self.status_label.pack(side="left", padx=18, pady=6)
        tk.Label(bar, text="Quy ước: dấu (+) = ngược chiều kim đồng hồ",
                 bg=PALETTE["header"], fg=PALETTE["dim"],
                 font=(FONT, 9)).pack(side="right", padx=18, pady=6)

    def set_status(self, message, kind="ok"):
        """Đổi nội dung và màu thanh trạng thái."""
        color = {
            "ok": PALETTE["success"],
            "info": PALETTE["accent"],
            "error": PALETTE["danger"],
            "warn": PALETTE["warning"],
        }.get(kind, PALETTE["success"])
        self.status_var.set(message)
        self.status_label.config(fg=color)

    # ------------------------------------------------------------------
    # 10.8. CHUYỂN TAB
    # ------------------------------------------------------------------
    def show_tab(self, key):
        """Đưa trang được chọn lên trên và tô sáng nút tab tương ứng."""
        self.active_tab = key
        for k, page in self.pages.items():
            if k == key:
                page.tkraise()
        for k, btn in self.tab_buttons.items():
            if k == key:
                btn.configure(bg=PALETTE["accent"], fg=PALETTE["bg"])
            else:
                btn.configure(bg=PALETTE["card"], fg=PALETTE["muted"])

    # ------------------------------------------------------------------
    # 10.9. ĐỌC / NẠP THÔNG SỐ
    # ------------------------------------------------------------------
    def _fill_form(self, params):
        """Nạp một bộ thông số vào các ô nhập (không tự động tính)."""
        for key, _label in FIELDS:
            if key in self.vars:
                value = params.get(key, 0.0)
                self.vars[key].set(
                    f"{value:g}" if isinstance(value, (int, float))
                    else str(value)
                )
        for key, _label in DIR_FIELDS:
            if key in self.dir_vars:
                self.dir_vars[key].set(params.get(key, "cùng"))

    def _read_params(self):
        """
        Đọc và kiểm tra dữ liệu từ form.
        Chấp nhận dấu phẩy thập phân (ví dụ 4,5) như m.py.
        """
        p = {}
        for key, label in FIELDS:
            raw = self.vars[key].get().strip().replace(",", ".")
            if raw == "":
                raise ValueError(f"Chưa nhập '{label}'.")
            try:
                value = float(raw)
            except ValueError:
                raise ValueError(
                    f"Giá trị không hợp lệ tại '{label}': '{raw}'"
                )
            if not np.isfinite(value):
                raise ValueError(f"Giá trị tại '{label}' phải là số hữu hạn.")
            p[key] = value
        for key, label in DIR_FIELDS:
            value = self.dir_vars[key].get()
            if value not in ("cùng", "ngược"):
                raise ValueError(f"Chưa chọn '{label}'.")
            p[key] = value

        if p["omega2"] < 0 or p["eps2"] < 0:
            raise ValueError(
                "Độ lớn |ω₂| và |ε₂| phải ≥ 0; chiều quay chọn ở ô bên cạnh."
            )
        if min(p["L1"], p["L2"], p["L3"], p["L4"]) <= 0:
            raise ValueError("Chiều dài các khâu L1, L2, L3, L4 phải > 0.")
        if p["lBM"] > p["L3"]:
            raise ValueError("lBM phải ≤ L3 = lBC (M nằm trên đoạn BC).")
        if p["lBM"] < 0 or p["lME"] < 0:
            raise ValueError("lBM và lME phải ≥ 0.")
        return p

    def load_preset(self, name):
        """Nạp phương án mẫu rồi tính ngay."""
        self._fill_form(PRESETS[name])
        self.on_compute()
        if self.last_params is not None:
            self.set_status(f"Đã nạp {name}.", "info")

    # ==========================================================================
    # PHẦN 5 — CÁC METHOD ĐIỀU PHỐI, MÔ PHỎNG, LỊCH SỬ, XUẤT FILE
    # ==========================================================================
    # ------------------------------------------------------------------
    # 10.10. TÍNH TOÁN VÀ CẬP NHẬT KẾT QUẢ
    # ------------------------------------------------------------------
    def on_compute(self, silent=False):
        """
        Luồng chính:
          1. Đọc thông số + giải vị trí.
          2. Giải vận tốc, gia tốc (nếu được).
          3. Cập nhật toàn bộ ô kết quả chỉ xem và các hình.
          4. Nạp lại mô phỏng theo thông số mới.
          5. Lưu lịch sử nếu người dùng chủ động tính.
        """
        try:
            p = self._read_params()
            pts = solve_positions(p)
        except ValueError as ex:
            self._clear_results(str(ex))
            self.set_status(f"Lỗi: {ex}", "error")
            if not silent:
                messagebox.showerror("Lỗi dữ liệu", str(ex))
            return

        # Giải vận tốc và gia tốc; lỗi ở bước này không xóa lược đồ.
        vel = acc = None
        err_vel = err_acc = None
        try:
            vel = solve_velocities(p, pts)
        except ValueError as ex:
            err_vel = str(ex)
        if vel is not None:
            try:
                acc = solve_accelerations(p, pts, vel)
            except ValueError as ex:
                err_acc = str(ex)
        else:
            err_acc = ("Không thể tính gia tốc vì chưa xác định được "
                       "vận tốc.")

        self.last_params = p
        self.last_pts = pts
        self.last_vel = vel
        self.last_acc = acc
        self.last_err_vel = err_vel
        self.last_err_acc = err_acc

        # Vẽ lược đồ kèm vectơ nếu người dùng đã bật tùy chọn.
        self._draw_structure_mechanism()

        # Cập nhật các khối kết quả chỉ xem.
        self.txt_struct.set_text(structure_text(p))
        self._update_velocity_view(vel, err_vel)
        self._update_acceleration_view(acc, err_acc)
        self.last_report = full_report(p, pts, vel, acc, err_vel, err_acc)
        self.txt_report.set_text(self.last_report)

        # Nạp lại mô phỏng với thông số mới.
        self._reset_sim(p)

        # Lưu lịch sử khi người dùng bấm nút hoặc Enter/preset.
        if not silent:
            self._add_history(p)
            if vel is None or acc is None:
                self.set_status(
                    "Đã vẽ lược đồ nhưng chưa giải được vận tốc/gia tốc.",
                    "warn")
            else:
                self.set_status(
                    "Tính toán thành công. Kết quả đang ở dạng chỉ xem.",
                    "ok")

    def _clear_results(self, message):
        """Xóa/ghi đè toàn bộ kết quả khi thông số không hợp lệ."""
        self._stop_sim()
        self.last_params = None
        self.last_pts = None
        self.last_vel = None
        self.last_acc = None
        self.last_err_vel = None
        self.last_err_acc = None
        self.last_report = message

        self.txt_struct.set_text("KHÔNG THỂ PHÂN TÍCH\n\n" + message)
        self.txt_report.set_text("KHÔNG THỂ TÍNH TOÁN\n\n" + message)
        self.card_w3.set("—", "")
        self.card_w4.set("—", "")
        self.card_e3.set("—", "")
        self.card_e4.set("—", "")
        self.tbl_vel.set_rows([])
        self.tbl_acc.set_rows([])
        self.txt_vel_note.set_text(message)
        self.txt_acc_note.set_text(message)
        show_figure_message(self.fig_struct, self.ax_struct,
                            self.canvas_struct, message)
        show_figure_message(self.fig_vel, self.ax_vel, self.canvas_vel,
                            "Chưa có họa đồ vận tốc")
        show_figure_message(self.fig_acc, self.ax_acc, self.canvas_acc,
                            "Chưa có họa đồ gia tốc")
        show_figure_message(self.fig_sim, self.ax_sim, self.canvas_sim,
                            message)
        self.txt_sim_info.set_text(message)
        self.trails = {"B": [], "C": [], "M": [], "E": []}

    def _draw_structure_mechanism(self):
        """Vẽ lại lược đồ cấu trúc với tùy chọn vectơ hiện hành."""
        if self.last_params is None or self.last_pts is None:
            return
        draw_mechanism(
            self.ax_struct, self.last_pts, self.last_params,
            vel=self.last_vel, acc=self.last_acc,
            show_v=self.show_vel_var.get(),
            show_a=self.show_acc_var.get(),
        )
        self.canvas_struct.draw_idle()

    def _on_vector_toggle(self):
        """Bật/tắt vectơ vận tốc, gia tốc trên lược đồ và mô phỏng."""
        self._draw_structure_mechanism()
        self._sim_draw()
        enabled = [
            name for name, var in (
                ("vận tốc", self.show_vel_var),
                ("gia tốc", self.show_acc_var),
            ) if var.get()
        ]
        self.set_status(
            "Vectơ trên lược đồ: " + (", ".join(enabled) if enabled else "tắt")
            + ".", "info")

    def _update_velocity_view(self, vel, error=None):
        """Cập nhật thẻ ω3/ω4, bảng và họa đồ vận tốc."""
        if vel is None:
            self.card_w3.set("—", "")
            self.card_w4.set("—", "")
            self.tbl_vel.set_rows([])
            self.txt_vel_note.set_text(error or "Không có dữ liệu.")
            show_figure_message(self.fig_vel, self.ax_vel, self.canvas_vel,
                                error or "Chưa có họa đồ vận tốc")
            return

        self.card_w3.set(f"{abs(vel['w3']):.4f} rad/s", rot_text(vel["w3"]))
        self.card_w4.set(f"{abs(vel['w4']):.4f} rad/s", rot_text(vel["w4"]))
        self.tbl_vel.set_rows(vector_table_rows(vel, "v"))

        # Ghi chú công thức chỉ xem, kèm nhắc quy ước dấu.
        self.txt_vel_note.set_text(
            "vB = ω₂ × AB\n"
            "vC = vB + ω₃ × BC = vD + ω₄ × DC  (vD = 0)\n"
            "vM = vB + ω₃ × BM ; vE = vB + ω₃ × BE\n\n"
            f"ω₂ = {abs(vel['w2']):.4f} rad/s ({rot_text(vel['w2'])})\n"
            "Hướng trong bảng đo từ trục Ox, ngược chiều kim đồng hồ.\n"
            "Họa đồ bên trái vẽ đúng phương, chiều, tỉ lệ tương đối."
        )
        draw_velocity_polygon(self.ax_vel, vel)
        self.canvas_vel.draw_idle()

    def _update_acceleration_view(self, acc, error=None):
        """Cập nhật thẻ ε3/ε4, bảng và họa đồ gia tốc."""
        if acc is None:
            self.card_e3.set("—", "")
            self.card_e4.set("—", "")
            self.tbl_acc.set_rows([])
            self.txt_acc_note.set_text(error or "Không có dữ liệu.")
            show_figure_message(self.fig_acc, self.ax_acc, self.canvas_acc,
                                error or "Chưa có họa đồ gia tốc")
            return

        self.card_e3.set(f"{abs(acc['e3']):.4f} rad/s²",
                         rot_text(acc["e3"], "ε"))
        self.card_e4.set(f"{abs(acc['e4']):.4f} rad/s²",
                         rot_text(acc["e4"], "ε"))
        self.tbl_acc.set_rows(vector_table_rows(acc, "a"))

        self.txt_acc_note.set_text(
            "aB = ε₂ × AB − ω₂²·AB\n"
            "aC = aB + ε₃ × BC − ω₃²·BC\n"
            "   = aD + ε₄ × DC − ω₄²·DC  (aD = 0)\n"
            "aM = aB + ε₃ × BM − ω₃²·BM ; aE tương tự.\n\n"
            f"ε₂ = {abs(acc['e2']):.4f} rad/s² ({rot_text(acc['e2'], 'ε')})\n"
            "Hướng trong bảng đo từ trục Ox, ngược chiều kim đồng hồ."
        )
        draw_accel_polygon(self.ax_acc, acc)
        self.canvas_acc.draw_idle()

    # ------------------------------------------------------------------
    # 10.11. MÔ PHỎNG CHUYỂN ĐỘNG
    # ------------------------------------------------------------------
    def _reset_sim(self, p=None):
        """
        Đặt mô phỏng về góc φ2 của thông số vừa tính và xóa quỹ đạo cũ.
        Không tự chạy để người dùng chủ động bấm CHẠY.
        """
        self._stop_sim()
        if p is None:
            p = self.last_params
        if p is None:
            return
        self.sim_phi = p["phi2"] % 360.0
        self.sim_phi_var.set(self.sim_phi)
        self.lbl_phi.config(text=f"φ₂ = {self.sim_phi:.1f}°")
        self.trails = {"B": [], "C": [], "M": [], "E": []}
        self._sim_draw()

    def _stop_sim(self):
        """Dừng vòng lặp after() của mô phỏng và cập nhật nút."""
        self.sim_running = False
        if self.sim_after is not None:
            try:
                self.after_cancel(self.sim_after)
            except tk.TclError:
                pass
            self.sim_after = None
        if hasattr(self, "btn_run"):
            self.btn_run.config(text="▶  CHẠY")

    def toggle_run(self):
        """Bật/tắt hoạt ảnh mô phỏng."""
        if self.sim_running:
            self._stop_sim()
            return
        if self.last_params is None:
            messagebox.showwarning(
                "Chưa có thông số",
                "Hãy nhập thông số hợp lệ và bấm TÍNH TOÁN trước.")
            return
        self.sim_running = True
        self.btn_run.config(text="⏸  TẠM DỪNG")
        self._sim_tick()

    def reset_simulation(self):
        """Đưa góc φ2 về giá trị ban đầu và xóa quỹ đạo."""
        self._stop_sim()
        if self.last_params is not None:
            self.sim_phi = self.last_params["phi2"] % 360.0
        else:
            self.sim_phi = 0.0
        self.sim_phi_var.set(self.sim_phi)
        self.trails = {"B": [], "C": [], "M": [], "E": []}
        self._sim_draw()

    def on_phi_scale(self, value):
        """Kéo thanh trượt φ2 khi đang tạm dừng."""
        if self.sim_running:
            return
        self.sim_phi = float(value) % 360.0
        self.lbl_phi.config(text=f"φ₂ = {self.sim_phi:.1f}°")
        self._sim_draw()

    def redraw_simulation(self):
        """Vẽ lại mô phỏng (dùng khi bật/tắt hiển thị quỹ đạo)."""
        if not self.ve_quy_dao_var.get():
            self.trails = {"B": [], "C": [], "M": [], "E": []}
        self._sim_draw()

    def _sim_tick(self):
        """Một khung hình: quay φ₂ theo chiều ω₂ đã chọn rồi vẽ lại."""
        self.sim_after = None
        if not self.sim_running:
            return
        speed = float(self.sim_speed_var.get())
        way = 1
        if self.last_params is not None and signed_w2(self.last_params) < 0:
            way = -1
        self.sim_phi = (self.sim_phi + way * speed) % 360.0
        self.sim_phi_var.set(self.sim_phi)
        self.lbl_phi.config(text=f"φ₂ = {self.sim_phi:.1f}°")
        self._sim_draw()
        self.sim_after = self.after(33, self._sim_tick)

    def _sim_draw(self):
        """Vẽ cơ cấu tại góc hiện tại, kèm quỹ đạo và thông tin chỉ xem."""
        if self.last_params is None:
            show_figure_message(self.fig_sim, self.ax_sim, self.canvas_sim,
                                "Chưa có thông số hợp lệ để mô phỏng.")
            return

        p = dict(self.last_params)
        p["phi2"] = self.sim_phi
        try:
            pts = solve_positions(p)
        except ValueError as ex:
            show_figure_message(self.fig_sim, self.ax_sim, self.canvas_sim,
                                f"Vị trí không hợp lệ tại φ₂ = "
                                f"{self.sim_phi:.1f}°.\n{ex}")
            self.txt_sim_info.set_text(
                f"φ₂ = {self.sim_phi:.1f}°\n\nVị trí không hợp lệ:\n{ex}")
            return

        # Chỉ tích lũy quỹ đạo khi người dùng bật tùy chọn.
        if self.ve_quy_dao_var.get():
            for key in ("B", "C", "M", "E"):
                self.trails[key].append(pts[key].copy())
                if len(self.trails[key]) > 900:
                    self.trails[key].pop(0)

        # Vectơ chỉ được giải khi cần hiển thị để mô phỏng nhẹ hơn.
        vel = acc = None
        want_v = self.show_vel_var.get()
        want_a = self.show_acc_var.get()
        if want_v or want_a:
            try:
                vel = solve_velocities(p, pts)
                if want_a:
                    acc = solve_accelerations(p, pts, vel)
            except ValueError:
                vel = acc = None

        draw_mechanism(
            self.ax_sim, pts, p,
            trails=self.trails if self.ve_quy_dao_var.get() else None,
            title=f"Mô phỏng cơ cấu — φ₂ = {self.sim_phi:.1f}°",
            vel=vel, acc=acc, show_v=want_v, show_a=want_a,
        )
        self.canvas_sim.draw_idle()

        # Bảng thông tin hiện tại chỉ xem.
        state = "Đang chạy" if self.sim_running else "Tạm dừng"
        self.txt_sim_info.set_text(
            f"Trạng thái : {state}\n"
            f"φ₂         : {self.sim_phi:7.1f}°\n"
            f"ω₂         : {abs(self.last_params['omega2']):g} rad/s "
            f"({rot_text(signed_w2(self.last_params))})\n"
            f"ε₂         : {abs(self.last_params['eps2']):g} rad/s² "
            f"({rot_text(signed_e2(self.last_params), 'ε')})\n"
            f"--------------------------------\n"
            f"B = ({pts['B'][0]:8.3f} ; {pts['B'][1]:8.3f})\n"
            f"C = ({pts['C'][0]:8.3f} ; {pts['C'][1]:8.3f})\n"
            f"M = ({pts['M'][0]:8.3f} ; {pts['M'][1]:8.3f})\n"
            f"E = ({pts['E'][0]:8.3f} ; {pts['E'][1]:8.3f})\n"
            f"--------------------------------\n"
            f"Quỹ đạo   : {'BẬT' if self.ve_quy_dao_var.get() else 'TẮT'}\n"
            f"Vectơ v   : {'BẬT' if want_v else 'TẮT'}\n"
            f"Vectơ a   : {'BẬT' if want_a else 'TẮT'}\n"
            f"Điểm lưu  : {len(self.trails['M'])}"
        )

    # ------------------------------------------------------------------
    # 10.12. LỊCH SỬ THÔNG SỐ
    # ------------------------------------------------------------------
    def _refresh_history_list(self):
        """Đồng bộ Listbox với danh sách lịch sử trong bộ nhớ."""
        self.hist_lb.delete(0, "end")
        for item in self.history:
            self.hist_lb.insert("end", history_label(item))

    def _add_history(self, p):
        """Thêm một bộ thông số vào lịch sử; trùng bộ cũ thì chỉ cập nhật giờ."""
        if self.history and self.history[0]["params"] == p:
            self.history[0]["time"] = datetime.now().strftime("%d/%m %H:%M:%S")
        else:
            self.history.insert(
                0, dict(time=datetime.now().strftime("%d/%m %H:%M:%S"),
                        params=dict(p)))
            del self.history[HISTORY_MAX:]
        save_history(self.history)
        self._refresh_history_list()

    def _selected_history_index(self):
        """Lấy chỉ số dòng đang chọn; báo nếu chưa chọn dòng nào."""
        selection = self.hist_lb.curselection()
        if not selection:
            messagebox.showinfo("Lịch sử",
                                "Hãy chọn một dòng trong lịch sử.")
            return None
        return selection[0]

    def load_selected_history(self):
        """Nạp bộ thông số đang chọn rồi tính lại toàn bộ."""
        index = self._selected_history_index()
        if index is None:
            return
        self._fill_form(self.history[index]["params"])
        self.on_compute()
        if self.last_params is not None:
            self.set_status("Đã nạp thông số từ lịch sử.", "info")

    def delete_selected_history(self):
        """Xóa một dòng lịch sử đang chọn."""
        index = self._selected_history_index()
        if index is None:
            return
        del self.history[index]
        save_history(self.history)
        self._refresh_history_list()
        self.set_status("Đã xóa một dòng lịch sử.", "info")

    def clear_history(self):
        """Xóa toàn bộ lịch sử sau khi người dùng xác nhận."""
        if not self.history:
            return
        if messagebox.askyesno("Xóa lịch sử",
                               "Xóa toàn bộ lịch sử thông số đã nhập?"):
            self.history = []
            save_history(self.history)
            self._refresh_history_list()
            self.set_status("Đã xóa toàn bộ lịch sử.", "info")

    # ------------------------------------------------------------------
    # 10.13. XUẤT KẾT QUẢ
    # ------------------------------------------------------------------
    def export_results(self):
        """
        Lưu:
          - ảnh lược đồ cơ cấu;
          - ảnh họa đồ vận tốc (nếu có);
          - ảnh họa đồ gia tốc (nếu có);
          - báo cáo TXT đầy đủ.
        Người dùng chọn tên tệp gốc; các tệp phụ được thêm hậu tố.
        """
        if self.last_params is None or self.last_pts is None:
            messagebox.showwarning(
                "Chưa có kết quả",
                "Hãy nhập thông số hợp lệ và tính toán trước khi lưu.")
            return

        default_name = "co_cau_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Lưu kết quả (ảnh lược đồ, họa đồ và báo cáo TXT)",
            defaultextension=".png",
            initialfile=default_name,
            filetypes=[("Ảnh PNG", "*.png"), ("Ảnh PDF", "*.pdf")],
        )
        if not path:
            return

        base, ext = os.path.splitext(path)
        ext = ext if ext.lower() in (".png", ".pdf") else ".png"
        img_main = base + ext
        img_vel = base + "_hoa_do_van_toc" + ext
        img_acc = base + "_hoa_do_gia_toc" + ext
        txt_path = base + ".txt"
        saved = [img_main]

        try:
            self.fig_struct.savefig(
                img_main, dpi=200, bbox_inches="tight",
                facecolor=self.fig_struct.get_facecolor())
            if self.last_vel is not None:
                self.fig_vel.savefig(
                    img_vel, dpi=200, bbox_inches="tight",
                    facecolor=self.fig_vel.get_facecolor())
                saved.append(img_vel)
            if self.last_acc is not None:
                self.fig_acc.savefig(
                    img_acc, dpi=200, bbox_inches="tight",
                    facecolor=self.fig_acc.get_facecolor())
                saved.append(img_acc)
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(self.last_report)
            saved.append(txt_path)
        except OSError as ex:
            messagebox.showerror("Lỗi lưu file", str(ex))
            return

        messagebox.showinfo("Đã lưu", "Đã lưu:\n" +
                            "\n".join("- " + item for item in saved))


# ============================================================================
# ĐIỂM VÀO CHƯƠNG TRÌNH
# ============================================================================
if __name__ == "__main__":
    app = CoCauDashboard()
    app.mainloop()
