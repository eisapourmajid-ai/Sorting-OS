# -*- coding: utf-8 -*-
"""SORTING OS - offline desktop MVP. Python 3.8+ standard library only."""
from __future__ import annotations
import csv
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from database import Database, now_iso
from accounting_core import AccountingBook, parse_amount_to_rial, format_money

APP_NAME = "SORTING OS | مدیریت سورتینگ"
ACTOR = os.environ.get("SORTING_OS_USER", "مدیر مجموعه")


def app_data_dir():
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "SORTING_OS")
    os.makedirs(path, exist_ok=True)
    return path


class SortingApp(tk.Tk):
    def __init__(self, db_path=None):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(990, 630)
        self.configure(bg="#f3f5f7")
        self.db = Database(db_path or os.path.join(app_data_dir(), "sorting_os.sqlite3"))
        self.accounting = AccountingBook(self.db.path)
        self.current_page = None
        self.selected_party_id = None
        self.selected_party_row = None
        self._configure_style()
        self._build_shell()
        self.show_dashboard()

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f3f5f7")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f3f5f7", foreground="#1c2633", font=("Tahoma", 10))
        style.configure("Title.TLabel", background="#f3f5f7", foreground="#182433", font=("Tahoma", 19, "bold"))
        style.configure("Sub.TLabel", background="#f3f5f7", foreground="#64748b", font=("Tahoma", 9))
        style.configure("Metric.TLabel", background="#ffffff", foreground="#14243a", font=("Tahoma", 20, "bold"))
        style.configure("MetricTitle.TLabel", background="#ffffff", foreground="#64748b", font=("Tahoma", 10))
        style.configure("TButton", font=("Tahoma", 9), padding=(12, 8))
        style.configure("Primary.TButton", font=("Tahoma", 9, "bold"), padding=(14, 8))
        style.configure("Treeview", font=("Tahoma", 9), rowheight=29)
        style.configure("Treeview.Heading", font=("Tahoma", 9, "bold"))
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=5)

    def _build_shell(self):
        header = tk.Frame(self, bg="#14273d", height=70)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="SORTING OS", bg="#14273d", fg="#ffffff", font=("Tahoma", 17, "bold")).pack(side="right", padx=24, pady=15)
        tk.Label(header, text="مدیریت یکپارچه عملیات سورتینگ", bg="#14273d", fg="#cbd5e1", font=("Tahoma", 10)).pack(side="right", pady=22)
        tk.Label(header, text="نسخه پایه محلی • بدون نیاز به اینترنت", bg="#14273d", fg="#a7f3d0", font=("Tahoma", 9)).pack(side="left", padx=20)

        body = tk.Frame(self, bg="#f3f5f7")
        body.pack(fill="both", expand=True)
        self.sidebar = tk.Frame(body, bg="#ffffff", width=205, padx=10, pady=18)
        self.sidebar.pack(side="right", fill="y")
        self.sidebar.pack_propagate(False)
        tk.Label(self.sidebar, text="ناوبری", bg="#ffffff", fg="#94a3b8", font=("Tahoma", 9, "bold"), anchor="e").pack(fill="x", padx=8, pady=(0, 12))
        navs = [("نمای کلی", self.show_dashboard), ("اشخاص و صاحبان کالا", self.show_parties), ("محموله‌ها", self.show_shipments),
                ("باسکول", self.show_weighings), ("فاکتورها", self.show_invoices), ("حسابداری و گزارش مالی", self.show_financials), ("ورود، خروج و پشتیبان", self.show_exchange), ("سوابق تغییرات", self.show_audit)]
        for label, command in navs:
            ttk.Button(self.sidebar, text=label, command=command).pack(fill="x", padx=2, pady=3)
        tk.Label(self.sidebar, text="ذخیره‌سازی محلی\n" + os.path.basename(self.db.path), bg="#ffffff", fg="#94a3b8", font=("Tahoma", 8), justify="right", wraplength=175, anchor="e").pack(side="bottom", fill="x", padx=5, pady=8)

        self.content = tk.Frame(body, bg="#f3f5f7", padx=24, pady=24)
        self.content.pack(side="left", fill="both", expand=True)
        footer = tk.Frame(self, bg="#e7edf2", height=27)
        footer.pack(side="bottom", fill="x")
        footer.pack_propagate(False)
        self.status_var = tk.StringVar(value="پایگاه داده محلی آماده است")
        tk.Label(footer, textvariable=self.status_var, bg="#e7edf2", fg="#526173", font=("Tahoma", 8), anchor="e").pack(side="right", padx=12)
        tk.Label(footer, text="Offline-first • اطلاعات در رایانه شما نگهداری می‌شود", bg="#e7edf2", fg="#526173", font=("Tahoma", 8), anchor="w").pack(side="left", padx=12)

    def _clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def _heading(self, title, subtitle=""):
        head = tk.Frame(self.content, bg="#f3f5f7")
        head.pack(fill="x", pady=(0, 18))
        ttk.Label(head, text=title, style="Title.TLabel", anchor="e").pack(fill="x")
        if subtitle:
            ttk.Label(head, text=subtitle, style="Sub.TLabel", anchor="e", justify="right").pack(fill="x", pady=(6, 0))

    def _entry(self, parent, label, variable=None, width=26, default=""):
        box = tk.Frame(parent, bg="#ffffff")
        tk.Label(box, text=label, bg="#ffffff", fg="#475569", font=("Tahoma", 9), anchor="e").pack(fill="x", pady=(0, 5))
        var = variable or tk.StringVar(value=default)
        ent = ttk.Entry(box, textvariable=var, width=width, justify="right")
        ent.pack(fill="x")
        return box, var, ent

    def _tree(self, parent, columns, headings, height=12):
        frame = tk.Frame(parent, bg="#ffffff")
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
        for col, title, width in headings:
            tree.heading(col, text=title, anchor="e")
            tree.column(col, width=width, anchor="e", stretch=True)
        ybar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        xbar = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _card(self, parent, title, value, note=""):
        f = tk.Frame(parent, bg="#ffffff", padx=18, pady=17, highlightthickness=1, highlightbackground="#e3e9ef")
        ttk.Label(f, text=title, style="MetricTitle.TLabel", anchor="e").pack(fill="x")
        ttk.Label(f, text=value, style="Metric.TLabel", anchor="e").pack(fill="x", pady=(9, 4))
        if note:
            tk.Label(f, text=note, bg="#ffffff", fg="#94a3b8", font=("Tahoma", 8), anchor="e").pack(fill="x")
        return f

    def show_dashboard(self):
        self._clear(); self.current_page = "dashboard"
        self._heading("نمای کلی مجموعه", "خلاصه از اطلاعات ثبت‌شده در پایگاه داده محلی؛ داده آزمایشی نمایش داده نمی‌شود.")
        counts = self.db.counts()
        metrics = tk.Frame(self.content, bg="#f3f5f7")
        metrics.pack(fill="x")
        cards = [self._card(metrics, "اشخاص فعال", str(counts["parties"]), "پرونده‌های فعال"),
                 self._card(metrics, "محموله‌های باز", str(counts["shipments"]), "به‌جز بسته‌شده‌ها"),
                 self._card(metrics, "قبض‌های باسکول", str(counts["weighings"]), "وزن‌کشی‌های ثبت‌شده"),
                 self._card(metrics, "فاکتورهای ثبت‌شده", str(counts["invoices"]), "پیش‌نویس و قطعی")]
        for i, c in enumerate(cards): c.grid(row=0, column=i, sticky="nsew", padx=5, pady=4)
        for i in range(4): metrics.columnconfigure(i, weight=1)
        lower = tk.Frame(self.content, bg="#f3f5f7")
        lower.pack(fill="both", expand=True, pady=(20, 0))
        left = tk.Frame(lower, bg="#ffffff", padx=18, pady=16, highlightthickness=1, highlightbackground="#e3e9ef")
        left.pack(side="right", fill="both", expand=True, padx=(0, 6))
        ttk.Label(left, text="شروع سریع", style="MetricTitle.TLabel", anchor="e").pack(fill="x", pady=(0, 12))
        for txt, cmd in [("ثبت شخص / صاحب کالا", self.show_parties), ("ثبت محموله ورودی", self.show_shipments), ("ثبت قبض باسکول", self.show_weighings), ("ثبت فاکتور", self.show_invoices), ("حسابداری و گزارش مالی", self.show_financials), ("خروجی Excel سازگار (CSV) / پشتیبان", self.show_exchange)]:
            ttk.Button(left, text=txt, command=cmd).pack(fill="x", pady=4)
        right = tk.Frame(lower, bg="#ffffff", padx=18, pady=16, highlightthickness=1, highlightbackground="#e3e9ef")
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))
        ttk.Label(right, text="شاخص‌های پایه", style="MetricTitle.TLabel", anchor="e").pack(fill="x", pady=(0, 12))
        for label, val in [("وزن دریافتی ثبت‌شده", self._number(counts["received_weight"]) + " کیلوگرم"), ("جمع مبلغ فاکتورهای قطعی", self._number(counts["invoice_amount"]) + " تومان"), ("فایل پایگاه داده", self.db.path)]:
            tk.Label(right, text=label, bg="#ffffff", fg="#64748b", font=("Tahoma", 9), anchor="e").pack(fill="x", pady=(6, 2))
            tk.Label(right, text=val, bg="#ffffff", fg="#14243d", font=("Tahoma", 10, "bold"), anchor="e", justify="right", wraplength=420).pack(fill="x")
        tk.Label(self.content, text="توجه: فاکتورهای پایه به دفترکل حسابداری به‌صورت خودکار ثبت نمی‌شوند. گزارش مالی فقط از اسناد حسابداری قطعی و متوازن ساخته می‌شود؛ صافی کامل، گردش چک و طراح حرفه‌ای چاپ هنوز نیازمند تکمیل‌اند.", bg="#f3f5f7", fg="#9a3412", font=("Tahoma", 9), anchor="e", justify="right", wraplength=900).pack(fill="x", pady=(16, 0))

    @staticmethod
    def _number(value):
        try: return format(float(value), ",.3f").rstrip("0").rstrip(".") if "." in format(float(value), ",.3f") else format(int(value), ",")
        except Exception: return str(value)

    def show_parties(self):
        self._clear(); self.current_page = "parties"; self.selected_party_id = None
        self._heading("اشخاص و صاحبان کالا", "هویت یکپارچه؛ تشابه نام هشدار ایجاد می‌کند و هرگز به‌تنهایی باعث ادغام خودکار نمی‌شود.")
        toolbar = tk.Frame(self.content, bg="#f3f5f7"); toolbar.pack(fill="x", pady=(0, 12))
        self.party_search = tk.StringVar()
        ttk.Entry(toolbar, textvariable=self.party_search, justify="right", width=32).pack(side="right", padx=(0, 8))
        ttk.Button(toolbar, text="جست‌وجو", command=self._refresh_parties).pack(side="right", padx=3)
        ttk.Button(toolbar, text="افزودن شخص", style="Primary.TButton", command=lambda: self._party_form()).pack(side="left", padx=3)
        ttk.Button(toolbar, text="ویرایش انتخاب‌شده", command=self._edit_selected_party).pack(side="left", padx=3)
        ttk.Button(toolbar, text="خروجی CSV", command=lambda: self.export_csv("parties")).pack(side="left", padx=3)
        self.party_tree = self._tree(self.content, ("id", "code", "name", "phone", "nid", "roles", "active"), [("id","ID",55),("code","کد داخلی",155),("name","نام و نام خانوادگی",220),("phone","تلفن",120),("nid","کد ملی",120),("roles","نقش‌ها",160),("active","وضعیت",80)])
        self.party_tree.bind("<Double-1>", lambda e: self._edit_selected_party())
        self._refresh_parties()

    def _refresh_parties(self):
        for item in self.party_tree.get_children(): self.party_tree.delete(item)
        for p in self.db.list_parties(self.party_search.get() if hasattr(self, "party_search") else ""):
            self.party_tree.insert("", "end", iid=str(p["id"]), values=(p["id"],p["code"],p["display_name"],p["phone"] or "",p["national_id"] or "",p["roles"],"فعال" if p["is_active"] else "غیرفعال"))

    def _edit_selected_party(self):
        sel = self.party_tree.selection()
        if not sel: messagebox.showinfo("انتخاب شخص", "ابتدا یک شخص را انتخاب کنید."); return
        with self.db.connect() as con: row = con.execute("SELECT * FROM parties WHERE id=?", (int(sel[0]),)).fetchone()
        self._party_form(row)

    def _party_form(self, existing=None):
        win = tk.Toplevel(self); win.title("ویرایش شخص" if existing else "شخص جدید"); win.configure(bg="#ffffff"); win.resizable(False, False)
        win.transient(self); win.grab_set(); win.geometry("500x470")
        tk.Label(win, text="پرونده شخص", bg="#ffffff", fg="#14243d", font=("Tahoma", 15, "bold"), anchor="e").pack(fill="x", padx=24, pady=(22, 5))
        tk.Label(win, text="نام الزامی است. پیش از ثبت، کد ملی بررسی می‌شود.", bg="#ffffff", fg="#64748b", font=("Tahoma", 9), anchor="e").pack(fill="x", padx=24, pady=(0, 14))
        form = tk.Frame(win, bg="#ffffff", padx=24); form.pack(fill="both", expand=True)
        vars_ = {}
        fields = [("display_name","نام و نام خانوادگی"),("phone","تلفن / موبایل"),("national_id","کد ملی"),("roles","نقش‌ها؛ با ویرگول جدا شود"),("address","نشانی")]
        for key, label in fields:
            box,var,_ = self._entry(form,label,width=40,default=(existing[key] or "") if existing and key in existing.keys() else ("مالک کالا" if key=="roles" else ""))
            box.pack(fill="x", pady=5); vars_[key]=var
        def save():
            try:
                pid=self.db.save_party({k:v.get() for k,v in vars_.items()}, party_id=existing["id"] if existing else None, actor=ACTOR)
                self.status_var.set("پرونده شخص ذخیره شد: %s" % pid); win.destroy(); self._refresh_parties()
                if self.current_page == "invoices": self.show_invoices()
            except Exception as exc: messagebox.showerror("ثبت انجام نشد", str(exc), parent=win)
        ttk.Button(win,text="ذخیره پرونده",command=save).pack(side="left", padx=24, pady=18)
        ttk.Button(win,text="انصراف",command=win.destroy).pack(side="left", pady=18)

    def show_shipments(self):
        self._clear(); self.current_page = "shipments"; self._heading("محموله‌ها", "ثبت ورودی و اتصال پایدار به مالک کالا؛ موجودی پیشرفته و عملیات سورتینگ در فازهای بعد تکمیل می‌شوند.")
        bar=tk.Frame(self.content,bg="#f3f5f7");bar.pack(fill="x",pady=(0,12))
        ttk.Button(bar,text="ثبت محموله ورودی",style="Primary.TButton",command=self._shipment_form).pack(side="right")
        ttk.Button(bar,text="خروجی CSV",command=lambda:self.export_csv("shipments")).pack(side="left")
        self.shipment_tree=self._tree(self.content,("id","code","owner","product","weight","date","status","notes"),[("id","ID",50),("code","کد محموله",200),("owner","مالک کالا",180),("product","محصول",150),("weight","وزن ورودی (کیلوگرم)",135),("date","زمان دریافت",155),("status","وضعیت",100),("notes","توضیحات",180)])
        self._refresh_shipments()

    def _refresh_shipments(self):
        for item in self.shipment_tree.get_children(): self.shipment_tree.delete(item)
        for s in self.db.list_shipments(): self.shipment_tree.insert("","end",values=(s["id"],s["code"],s["owner_name"],s["product_name"],self._number(s["received_weight"]),s["received_at"],s["status"],s["notes"] or ""))

    def _active_parties(self): return self.db.list_parties(active_only=True)

    def _shipment_form(self):
        parties=self._active_parties()
        if not parties: messagebox.showwarning("ابتدا شخص بسازید","برای ثبت محموله، ابتدا مالک کالا را در بخش اشخاص ثبت کنید.");return
        win=tk.Toplevel(self);win.title("ثبت محموله ورودی");win.geometry("540x430");win.configure(bg="#ffffff");win.transient(self);win.grab_set()
        tk.Label(win,text="محموله ورودی جدید",bg="#ffffff",fg="#14243d",font=("Tahoma",15,"bold"),anchor="e").pack(fill="x",padx=24,pady=(22,14))
        form=tk.Frame(win,bg="#ffffff",padx=24);form.pack(fill="both",expand=True)
        selected=tk.StringVar(value=parties[0]["display_name"])
        box=tk.Frame(form,bg="#ffffff");tk.Label(box,text="مالک کالا",bg="#ffffff",font=("Tahoma",9),anchor="e").pack(fill="x"); owner_combo=ttk.Combobox(box,textvariable=selected,values=[p["display_name"] for p in parties],state="readonly",justify="right",width=42);owner_combo.pack(fill="x");box.pack(fill="x",pady=6)
        product_box,product,_=self._entry(form,"نام محصول",width=42);product_box.pack(fill="x",pady=6)
        weight_box,weight,_=self._entry(form,"وزن دریافت‌شده (کیلوگرم)",width=42);weight_box.pack(fill="x",pady=6)
        notes_box,notes,_=self._entry(form,"توضیحات",width=42);notes_box.pack(fill="x",pady=6)
        def save():
            try:
                p=next(x for x in parties if x["display_name"]==selected.get())
                sid=self.db.create_shipment(p["id"],product.get(),weight.get(),notes=notes.get(),actor=ACTOR)
                self.status_var.set("محموله ثبت شد: %s"%sid);win.destroy();self._refresh_shipments()
            except Exception as exc:messagebox.showerror("ثبت محموله ناموفق",str(exc),parent=win)
        row=tk.Frame(win,bg="#ffffff");row.pack(fill="x",padx=24,pady=18);ttk.Button(row,text="ذخیره محموله",command=save).pack(side="right");ttk.Button(row,text="انصراف",command=win.destroy).pack(side="right",padx=8)

    def show_weighings(self):
        self._clear(); self.current_page="weighings";self._heading("باسکول", "ثبت وزن ناخالص و خالی؛ وزن خالص در برنامه محاسبه می‌شود و ناخالص کمتر از خالی پذیرفته نمی‌شود.")
        bar=tk.Frame(self.content,bg="#f3f5f7");bar.pack(fill="x",pady=(0,12));ttk.Button(bar,text="ثبت قبض توزین",style="Primary.TButton",command=self._weighing_form).pack(side="right");ttk.Button(bar,text="خروجی CSV",command=lambda:self.export_csv("weighings")).pack(side="left")
        self.weighing_tree=self._tree(self.content,("id","code","type","shipment","plate","gross","tare","net","date","operator"),[("id","ID",45),("code","شماره قبض",190),("type","نوع",80),("shipment","محموله",175),("plate","پلاک",105),("gross","ناخالص",90),("tare","خالی",90),("net","خالص",90),("date","زمان توزین",150),("operator","اپراتور",120)])
        self._refresh_weighings()

    def _refresh_weighings(self):
        for item in self.weighing_tree.get_children():self.weighing_tree.delete(item)
        for w in self.db.list_weighings():self.weighing_tree.insert("","end",values=(w["id"],w["code"],w["ticket_type"],w["shipment_code"] or "بدون اتصال",w["vehicle_plate"] or "",self._number(w["gross_weight"]),self._number(w["tare_weight"]),self._number(w["net_weight"]),w["weighed_at"],w["operator_name"] or ""))

    def _weighing_form(self):
        shipments=self.db.list_shipments()
        win=tk.Toplevel(self);win.title("ثبت قبض باسکول");win.geometry("560x540");win.configure(bg="#ffffff");win.transient(self);win.grab_set()
        tk.Label(win,text="قبض توزین جدید",bg="#ffffff",fg="#14243d",font=("Tahoma",15,"bold"),anchor="e").pack(fill="x",padx=24,pady=(22,14))
        form=tk.Frame(win,bg="#ffffff",padx=24);form.pack(fill="both",expand=True)
        type_var=tk.StringVar(value="ورودی")
        b=tk.Frame(form,bg="#ffffff");tk.Label(b,text="نوع توزین",bg="#ffffff",font=("Tahoma",9),anchor="e").pack(fill="x");ttk.Combobox(b,textvariable=type_var,values=["ورودی","خروجی","کنترلی"],state="readonly",justify="right").pack(fill="x");b.pack(fill="x",pady=4)
        ship_var=tk.StringVar(value="بدون اتصال")
        b=tk.Frame(form,bg="#ffffff");tk.Label(b,text="محموله مرتبط (اختیاری)",bg="#ffffff",font=("Tahoma",9),anchor="e").pack(fill="x");shipcombo=ttk.Combobox(b,textvariable=ship_var,values=["بدون اتصال"]+[s["code"]+" | "+s["owner_name"] for s in shipments],state="readonly",justify="right");shipcombo.pack(fill="x");b.pack(fill="x",pady=4)
        fields={}
        for k,l in [("plate","پلاک خودرو"),("driver","نام راننده"),("gross","وزن ناخالص (کیلوگرم)"),("tare","وزن خالی (کیلوگرم)"),("operator","نام اپراتور"),("notes","توضیحات")]:
            box,var,_=self._entry(form,l,width=42);box.pack(fill="x",pady=4);fields[k]=var
        net_var=tk.StringVar(value="وزن خالص محاسبه می‌شود")
        tk.Label(form,textvariable=net_var,bg="#ffffff",fg="#047857",font=("Tahoma",10,"bold"),anchor="e").pack(fill="x",pady=5)
        def compute(*_):
            try: net_var.set("وزن خالص: %s کیلوگرم"%self._number(float(fields["gross"].get())-float(fields["tare"].get())))
            except Exception: net_var.set("وزن خالص پس از ورود دو وزن محاسبه می‌شود")
        fields["gross"].trace_add("write",compute);fields["tare"].trace_add("write",compute)
        def save():
            try:
                shipment_id=None
                if ship_var.get()!="بدون اتصال": shipment_id=next(s["id"] for s in shipments if s["code"]==ship_var.get().split(" | ")[0])
                wid=self.db.create_weighing(type_var.get(),fields["gross"].get(),fields["tare"].get(),shipment_id,fields["plate"].get(),fields["driver"].get(),operator=fields["operator"].get(),notes=fields["notes"].get(),actor=ACTOR)
                self.status_var.set("قبض باسکول ثبت شد: %s"%wid);win.destroy();self._refresh_weighings()
            except Exception as exc:messagebox.showerror("ثبت قبض ناموفق",str(exc),parent=win)
        row=tk.Frame(win,bg="#ffffff");row.pack(fill="x",padx=24,pady=14);ttk.Button(row,text="ذخیره قبض",command=save).pack(side="right");ttk.Button(row,text="انصراف",command=win.destroy).pack(side="right",padx=8)

    def show_invoices(self):
        self._clear();self.current_page="invoices";self._heading("فاکتورها و اسناد مالی پایه", "ثبت فاکتور با اتصال به شخص و محموله؛ در این نسخه قطعی‌کردن صرفاً وضعیت سند است و هنوز سند حسابداری دوبل ایجاد نمی‌کند.")
        bar=tk.Frame(self.content,bg="#f3f5f7");bar.pack(fill="x",pady=(0,12));ttk.Button(bar,text="ثبت فاکتور",style="Primary.TButton",command=self._invoice_form).pack(side="right");ttk.Button(bar,text="خروجی CSV",command=lambda:self.export_csv("invoices")).pack(side="left")
        self.invoice_tree=self._tree(self.content,("id","code","party","type","date","amount","shipment","status","desc"),[("id","ID",45),("code","شماره داخلی",185),("party","طرف حساب",170),("type","نوع",100),("date","تاریخ سند",105),("amount","مبلغ (تومان)",130),("shipment","محموله",190),("status","وضعیت",90),("desc","شرح",160)])
        self._refresh_invoices()

    def _refresh_invoices(self):
        for item in self.invoice_tree.get_children():self.invoice_tree.delete(item)
        for i in self.db.list_invoices():self.invoice_tree.insert("","end",values=(i["id"],i["code"],i["party_name"],i["invoice_type"],i["document_date"],self._number(i["amount"]),i["shipment_code"] or "بدون اتصال",i["status"],i["description"] or ""))

    def _invoice_form(self):
        parties=self._active_parties();shipments=self.db.list_shipments()
        if not parties:messagebox.showwarning("ابتدا شخص بسازید","برای ثبت فاکتور حداقل یک طرف حساب لازم است.");return
        win=tk.Toplevel(self);win.title("ثبت فاکتور");win.geometry("560x510");win.configure(bg="#ffffff");win.transient(self);win.grab_set()
        tk.Label(win,text="سند فروش / خرید / هزینه",bg="#ffffff",fg="#14243d",font=("Tahoma",15,"bold"),anchor="e").pack(fill="x",padx=24,pady=(22,14))
        form=tk.Frame(win,bg="#ffffff",padx=24);form.pack(fill="both",expand=True)
        partyvar=tk.StringVar(value=parties[0]["display_name"]);kindvar=tk.StringVar(value="فروش");datevar=tk.StringVar(value=date.today().isoformat());statusvar=tk.StringVar(value="پیش‌نویس");shipvar=tk.StringVar(value="بدون اتصال")
        for label,var,values in [("طرف حساب",partyvar,[p["display_name"] for p in parties]),("نوع سند",kindvar,["فروش","خرید","هزینه","سایر"]),("وضعیت",statusvar,["پیش‌نویس","قطعی"]),("محموله مرتبط (اختیاری)",shipvar,["بدون اتصال"]+[s["code"]+" | "+s["owner_name"] for s in shipments])]:
            b=tk.Frame(form,bg="#ffffff");tk.Label(b,text=label,bg="#ffffff",font=("Tahoma",9),anchor="e").pack(fill="x");ttk.Combobox(b,textvariable=var,values=values,state="readonly",justify="right").pack(fill="x");b.pack(fill="x",pady=4)
        datebox,dateval,_=self._entry(form,"تاریخ سند (YYYY-MM-DD)",variable=datevar,width=42);datebox.pack(fill="x",pady=4)
        amountbox,amount,_=self._entry(form,"مبلغ کل (تومان)",width=42);amountbox.pack(fill="x",pady=4)
        descbox,desc,_=self._entry(form,"شرح سند",width=42);descbox.pack(fill="x",pady=4)
        def save():
            try:
                pid=next(p["id"] for p in parties if p["display_name"]==partyvar.get());shipment_id=None
                if shipvar.get()!="بدون اتصال":shipment_id=next(s["id"] for s in shipments if s["code"]==shipvar.get().split(" | ")[0])
                if not datevar.get().strip():raise ValueError("تاریخ سند الزامی است.")
                iid=self.db.create_invoice(pid,kindvar.get(),datevar.get().strip(),amount.get(),desc.get(),shipment_id,statusvar.get(),ACTOR)
                self.status_var.set("فاکتور ثبت شد: %s"%iid);win.destroy();self._refresh_invoices()
            except Exception as exc:messagebox.showerror("ثبت فاکتور ناموفق",str(exc),parent=win)
        row=tk.Frame(win,bg="#ffffff");row.pack(fill="x",padx=24,pady=16);ttk.Button(row,text="ذخیره سند",command=save).pack(side="right");ttk.Button(row,text="انصراف",command=win.destroy).pack(side="right",padx=8)

    def show_financials(self):
        self._clear(); self.current_page = "financials"
        self._heading("حسابداری و گزارش مالی", "گزارش‌ها فقط از دفترکل دوبل واقعی خوانده می‌شوند؛ فاکتورهای قدیمی/پایه بدون قاعده مصوب به‌طور خودکار به سند حسابداری تبدیل نمی‌شوند.")
        filter_panel = tk.Frame(self.content, bg="#ffffff", padx=14, pady=12, highlightthickness=1, highlightbackground="#e3e9ef")
        filter_panel.pack(fill="x", pady=(0, 12))
        self.fin_from_var = tk.StringVar(value=date.today().replace(day=1).isoformat())
        self.fin_to_var = tk.StringVar(value=date.today().isoformat())
        self.fin_unit_var = tk.StringVar(value="تومان")
        left = tk.Frame(filter_panel, bg="#ffffff"); left.pack(side="left", padx=6)
        tk.Label(left, text="از تاریخ (YYYY-MM-DD)", bg="#ffffff", fg="#475569", font=("Tahoma", 8)).pack(anchor="e")
        ttk.Entry(left, textvariable=self.fin_from_var, width=14, justify="right").pack()
        middle = tk.Frame(filter_panel, bg="#ffffff"); middle.pack(side="left", padx=6)
        tk.Label(middle, text="تا تاریخ / تاریخ ترازنامه", bg="#ffffff", fg="#475569", font=("Tahoma", 8)).pack(anchor="e")
        ttk.Entry(middle, textvariable=self.fin_to_var, width=14, justify="right").pack()
        unitbox = tk.Frame(filter_panel, bg="#ffffff"); unitbox.pack(side="left", padx=8)
        tk.Label(unitbox, text="واحد نمایش گزارش", bg="#ffffff", fg="#475569", font=("Tahoma", 8)).pack(anchor="e")
        ttk.Combobox(unitbox, textvariable=self.fin_unit_var, values=("ریال", "تومان", "میلیون تومان"), state="readonly", width=15).pack()
        actions = tk.Frame(self.content, bg="#f3f5f7"); actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="ثبت سند حسابداری", style="Primary.TButton", command=self._financial_post_dialog).pack(side="right", padx=3)
        for label, fn in [("تراز آزمایشی", self._financial_trial_balance), ("ترازنامه", self._financial_balance_sheet), ("سود و زیان", self._financial_income_statement), ("جریان وجوه نقد", self._financial_cash_flow), ("نسبت‌های تحلیلی", self._financial_ratios)]:
            ttk.Button(actions, text=label, command=fn).pack(side="right", padx=3)
        note = tk.Label(self.content, text="مبنای ذخیره‌سازی مبالغ: عدد صحیح ریال. ورود/نمایش تومان با ضریب دقیق ۱۰ انجام می‌شود؛ هیچ مبلغی با float ذخیره نمی‌شود. برای ثبت رسمی، سرفصل‌ها و طبقه‌بندی‌ها باید توسط مسئول مالی تأیید شوند.", bg="#f3f5f7", fg="#64748b", font=("Tahoma", 9), justify="right", anchor="e", wraplength=900)
        note.pack(fill="x", pady=(0, 8))
        self.fin_results = tk.Frame(self.content, bg="#f3f5f7")
        self.fin_results.pack(fill="both", expand=True)
        self._financial_render("برای مشاهده گزارش، یکی از گزارش‌های بالا را انتخاب کنید.", [], [])

    def _financial_date_range(self):
        start = (self.fin_from_var.get() or "").strip()
        end = (self.fin_to_var.get() or "").strip()
        if not start or not end:
            raise ValueError("تاریخ شروع و پایان را وارد کنید.")
        return start, end

    def _money_text(self, amount):
        return format_money(int(amount), self.fin_unit_var.get(), local_digits=True)

    def _financial_render(self, title, columns, rows):
        for child in self.fin_results.winfo_children(): child.destroy()
        title_label = tk.Label(self.fin_results, text=title, bg="#f3f5f7", fg="#14243d", font=("Tahoma", 12, "bold"), anchor="e")
        title_label.pack(fill="x", pady=(0, 8))
        if not columns:
            tk.Label(self.fin_results, text="برای این گزارش/بازه سند قطعی وجود ندارد؛ هیچ عدد نمونه‌ای جایگزین داده واقعی نشده است.", bg="#ffffff", fg="#64748b", font=("Tahoma", 10), anchor="e", padx=16, pady=24, justify="right", wraplength=850).pack(fill="both", expand=True)
            return
        tree = self._tree(self.fin_results, tuple(c[0] for c in columns), columns, height=15)
        for row in rows:
            tree.insert("", "end", values=tuple(row.get(c[0], "") for c in columns))
        if not rows:
            tree.insert("", "end", values=tuple("—" if i == 0 else "بدون داده قطعی" if i == 1 else "" for i, _ in enumerate(columns)))

    def _financial_trial_balance(self):
        try:
            start, end = self._financial_date_range()
            report = self.accounting.trial_balance(start, end)
            if not self.accounting.list_entries(start, end, limit=1):
                self._financial_render("تراز آزمایشی از %s تا %s" % (start, end), [], [])
                return
            rows = []
            for r in report["rows"]:
                if not any(r[k] for k in ("opening_debit_rial", "opening_credit_rial", "debit_rial", "credit_rial", "closing_debit_rial", "closing_credit_rial")):
                    continue
                rows.append({"code": r["account_code"], "name": r["account_name"], "od": self._money_text(r["opening_debit_rial"]), "oc": self._money_text(r["opening_credit_rial"]), "dr": self._money_text(r["debit_rial"]), "cr": self._money_text(r["credit_rial"]), "cd": self._money_text(r["closing_debit_rial"]), "cc": self._money_text(r["closing_credit_rial"])})
            t = report["totals"]
            rows.append({"code": "جمع", "name": "وضعیت توازن: " + ("متوازن" if report["is_balanced"] else "نامتوازن"), "od": self._money_text(t["opening_debit_rial"]), "oc": self._money_text(t["opening_credit_rial"]), "dr": self._money_text(t["debit_rial"]), "cr": self._money_text(t["credit_rial"]), "cd": self._money_text(t["closing_debit_rial"]), "cc": self._money_text(t["closing_credit_rial"])})
            self._financial_render("تراز آزمایشی از %s تا %s" % (start, end), [("code", "کد حساب", 80), ("name", "نام حساب", 200), ("od", "افتتاحیه بدهکار", 125), ("oc", "افتتاحیه بستانکار", 125), ("dr", "گردش بدهکار", 125), ("cr", "گردش بستانکار", 125), ("cd", "مانده بدهکار", 125), ("cc", "مانده بستانکار", 125)], rows)
        except Exception as exc: messagebox.showerror("تراز آزمایشی", str(exc), parent=self)

    def _financial_balance_sheet(self):
        try:
            end = (self.fin_to_var.get() or "").strip()
            report = self.accounting.balance_sheet(end)
            if not self.accounting.list_entries(date_to=end, limit=1):
                self._financial_render("ترازنامه تا %s" % end, [], [])
                return
            rows = []
            for title, key, normal in [("دارایی‌ها", "assets", "raw_net_rial"), ("بدهی‌ها", "liabilities", "raw_net_rial"), ("حقوق مالکانه", "equity", "raw_net_rial")]:
                rows.append({"code": "", "name": title, "amount": ""})
                for a in report[key]:
                    raw = a[normal]
                    value = raw if key == "assets" else -raw
                    if value:
                        rows.append({"code": a["code"], "name": a["name"], "amount": self._money_text(value)})
            rows.extend([
                {"code": "", "name": "سود/زیان انباشته‌نشده تا تاریخ گزارش", "amount": self._money_text(report["current_earnings_rial"])},
                {"code": "", "name": "جمع دارایی‌ها", "amount": self._money_text(report["assets_total_rial"])},
                {"code": "", "name": "جمع بدهی و حقوق مالکانه", "amount": self._money_text(report["liabilities_equity_total_rial"])},
                {"code": "", "name": "اختلاف تراز", "amount": self._money_text(report["difference_rial"])},
                {"code": "", "name": "کنترل توازن", "amount": "متوازن" if report["is_balanced"] else "نامتوازن؛ بررسی سندها و سرفصل‌ها"},
            ])
            self._financial_render("ترازنامه تا %s" % end, [("code", "کد", 100), ("name", "سرفصل", 360), ("amount", "مانده", 220)], rows)
        except Exception as exc: messagebox.showerror("ترازنامه", str(exc), parent=self)

    def _financial_income_statement(self):
        try:
            start, end = self._financial_date_range()
            report = self.accounting.income_statement(start, end)
            if not self.accounting.list_entries(start, end, limit=1):
                self._financial_render("صورت سود و زیان از %s تا %s" % (start, end), [], [])
                return
            rows = []
            rows.append({"code": "", "name": "درآمدها", "amount": ""})
            for a in report["revenues"]:
                if a["natural_balance_rial"]: rows.append({"code": a["code"], "name": a["name"], "amount": self._money_text(a["natural_balance_rial"])})
            rows.append({"code": "", "name": "جمع درآمد", "amount": self._money_text(report["revenue_total_rial"])})
            rows.append({"code": "", "name": "هزینه‌ها", "amount": ""})
            for a in report["expenses"]:
                if a["natural_balance_rial"]: rows.append({"code": a["code"], "name": a["name"], "amount": self._money_text(a["natural_balance_rial"])})
            rows.extend([{ "code": "", "name": "جمع هزینه", "amount": self._money_text(report["expense_total_rial"])}, {"code": "", "name": "سود / زیان خالص دوره", "amount": self._money_text(report["net_profit_rial"])}])
            self._financial_render("صورت سود و زیان از %s تا %s" % (start, end), [("code", "کد", 100), ("name", "سرفصل", 360), ("amount", "مبلغ", 220)], rows)
        except Exception as exc: messagebox.showerror("صورت سود و زیان", str(exc), parent=self)

    def _financial_cash_flow(self):
        try:
            start, end = self._financial_date_range()
            report = self.accounting.cash_flow_statement(start, end)
            if not self.accounting.list_entries(start, end, limit=1):
                self._financial_render("صورت جریان وجوه نقد از %s تا %s" % (start, end), [], [])
                return
            rows = [
                {"name": "جریان نقد عملیاتی", "amount": self._money_text(report["operating_rial"])},
                {"name": "جریان نقد سرمایه‌گذاری", "amount": self._money_text(report["investing_rial"])},
                {"name": "جریان نقد تأمین مالی", "amount": self._money_text(report["financing_rial"])},
                {"name": "سایر جریان‌ها", "amount": self._money_text(report["other_rial"])},
                {"name": "خالص تغییر نقد", "amount": self._money_text(report["net_change_rial"])},
                {"name": "نقد اول دوره", "amount": self._money_text(report["opening_cash_rial"])},
                {"name": "نقد پایان دوره", "amount": self._money_text(report["closing_cash_rial"])},
                {"name": "کنترل تطبیق", "amount": "تطبیق شد" if report["reconciles"] else "مغایرت؛ بررسی طبقه‌بندی و اسناد"},
            ]
            self._financial_render("صورت جریان وجوه نقد از %s تا %s" % (start, end), [("name", "شرح", 360), ("amount", "مبلغ", 220)], rows)
        except Exception as exc: messagebox.showerror("جریان وجوه نقد", str(exc), parent=self)

    def _financial_ratios(self):
        try:
            start, end = self._financial_date_range()
            r = self.accounting.financial_ratios(end, start, end)
            if not self.accounting.list_entries(date_to=end, limit=1):
                self._financial_render("نسبت‌های تحلیلی تا %s" % end, [], [])
                return
            def fmt_ratio(value, percent=False):
                if value is None: return "قابل محاسبه نیست"
                return (format(value * 100, ".2f") + "٪") if percent else (format(value, ".3f") + " برابر")
            rows = [
                {"name": "نسبت جاری (تخمینی بر پایه کد حساب)", "value": fmt_ratio(r["current_ratio"])},
                {"name": "بدهی به دارایی", "value": fmt_ratio(r["liabilities_to_assets"], True)},
                {"name": "حاشیه سود خالص دوره", "value": fmt_ratio(r["net_profit_margin"], True)},
                {"name": "دارایی‌ها", "value": self._money_text(r["assets_total_rial"])},
                {"name": "بدهی‌ها", "value": self._money_text(r["liabilities_total_rial"])},
                {"name": "سود / زیان خالص دوره", "value": self._money_text(r["net_profit_rial"])},
                {"name": "ملاحظه تحلیلی", "value": r["note"]},
            ]
            self._financial_render("نسبت‌های تحلیلی تا %s" % end, [("name", "شاخص", 330), ("value", "نتیجه", 400)], rows)
        except Exception as exc: messagebox.showerror("نسبت‌های تحلیلی", str(exc), parent=self)

    def _financial_post_dialog(self):
        win = tk.Toplevel(self); win.title("ثبت سند حسابداری متوازن"); win.geometry("1120x650"); win.transient(self)
        win.configure(bg="#f3f5f7")
        tk.Label(win, text="ثبت سند دوبل — مبلغ‌ها در پایگاه داده به ریال صحیح ذخیره می‌شوند", bg="#f3f5f7", fg="#14243d", font=("Tahoma", 13, "bold"), anchor="e").pack(fill="x", padx=18, pady=(16, 4))
        tk.Label(win, text="تاریخ با قالب YYYY-MM-DD | هر ردیف فقط بدهکار یا بستانکار | سند نامتوازن ثبت نمی‌شود", bg="#f3f5f7", fg="#64748b", font=("Tahoma", 9), anchor="e").pack(fill="x", padx=18, pady=(0, 10))
        header = tk.Frame(win, bg="#ffffff", padx=12, pady=10); header.pack(fill="x", padx=18)
        datevar = tk.StringVar(value=date.today().isoformat()); descvar = tk.StringVar(); unitvar = tk.StringVar(value="تومان")
        for label, var, width in [("تاریخ سند", datevar, 16), ("شرح سند", descvar, 48)]:
            box = tk.Frame(header, bg="#ffffff"); box.pack(side="right", padx=7)
            tk.Label(box, text=label, bg="#ffffff", fg="#475569", font=("Tahoma", 9)).pack(anchor="e")
            ttk.Entry(box, textvariable=var, width=width, justify="right").pack()
        box = tk.Frame(header, bg="#ffffff"); box.pack(side="right", padx=7)
        tk.Label(box, text="واحد ورود", bg="#ffffff", fg="#475569", font=("Tahoma", 9)).pack(anchor="e")
        ttk.Combobox(box, textvariable=unitvar, values=("ریال", "تومان"), state="readonly", width=12).pack()
        account_opts = ["%s | %s" % (a["code"], a["name"]) for a in self.accounting.list_accounts()]
        panel = tk.Frame(win, bg="#ffffff", padx=10, pady=8); panel.pack(fill="both", expand=True, padx=18, pady=10)
        headings = ["حساب", "بدهکار", "بستانکار", "شرح ردیف"]
        for col, label in enumerate(headings):
            tk.Label(panel, text=label, bg="#ffffff", fg="#475569", font=("Tahoma", 9, "bold")).grid(row=0, column=col, padx=4, pady=4, sticky="ew")
        line_vars = []
        for i in range(8):
            av, dv, cv, mv = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
            ttk.Combobox(panel, textvariable=av, values=account_opts, width=34).grid(row=i+1, column=0, padx=4, pady=3, sticky="ew")
            ttk.Entry(panel, textvariable=dv, width=20, justify="right").grid(row=i+1, column=1, padx=4, pady=3, sticky="ew")
            ttk.Entry(panel, textvariable=cv, width=20, justify="right").grid(row=i+1, column=2, padx=4, pady=3, sticky="ew")
            ttk.Entry(panel, textvariable=mv, width=30, justify="right").grid(row=i+1, column=3, padx=4, pady=3, sticky="ew")
            line_vars.append((av, dv, cv, mv))
        for col, width in enumerate((3, 2, 2, 3)): panel.columnconfigure(col, weight=width)
        def save_entry():
            try:
                lines = []
                for av, dv, cv, mv in line_vars:
                    label = av.get().strip()
                    debit_raw, credit_raw = dv.get().strip(), cv.get().strip()
                    if not label and not debit_raw and not credit_raw: continue
                    if not label: raise ValueError("برای ردیف دارای مبلغ، حساب را انتخاب کنید.")
                    code = label.split(" | ", 1)[0]
                    debit = parse_amount_to_rial(debit_raw or "0", unitvar.get())
                    credit = parse_amount_to_rial(credit_raw or "0", unitvar.get())
                    lines.append({"account_code": code, "debit_rial": debit, "credit_rial": credit, "description": mv.get().strip()})
                entry_id = self.accounting.post_entry(datevar.get().strip(), descvar.get().strip(), lines, actor=ACTOR, source_type="manual")
                self.status_var.set("سند حسابداری قطعی و متوازن ثبت شد: %s" % entry_id)
                win.destroy(); self._financial_trial_balance()
                messagebox.showinfo("ثبت سند", "سند حسابداری متوازن با شناسه %s ثبت شد." % entry_id, parent=self)
            except Exception as exc: messagebox.showerror("ثبت سند ناموفق", str(exc), parent=win)
        buttons = tk.Frame(win, bg="#f3f5f7"); buttons.pack(fill="x", padx=18, pady=(0, 14))
        ttk.Button(buttons, text="ثبت قطعی سند", style="Primary.TButton", command=save_entry).pack(side="right")
        ttk.Button(buttons, text="انصراف", command=win.destroy).pack(side="right", padx=8)

    def show_exchange(self):
        self._clear();self.current_page="exchange";self._heading("ورود، خروج و پشتیبان", "خروجی CSV با UTF-8 و BOM برای بازشدن بهتر در Excel؛ ورود اشخاص با پیش‌نمایش و عدم ادغام خودکار بر اساس نام.")
        panel=tk.Frame(self.content,bg="#ffffff",padx=22,pady=22,highlightthickness=1,highlightbackground="#e3e9ef");panel.pack(fill="x",pady=(0,16))
        tk.Label(panel,text="خروجی داده",bg="#ffffff",fg="#14243d",font=("Tahoma",12,"bold"),anchor="e").pack(fill="x",pady=(0,10))
        row=tk.Frame(panel,bg="#ffffff");row.pack(fill="x")
        for ent,label in [("parties","اشخاص"),("shipments","محموله‌ها"),("weighings","باسکول"),("invoices","فاکتورها")]:ttk.Button(row,text="خروجی "+label,command=lambda e=ent:self.export_csv(e)).pack(side="right",padx=4)
        panel2=tk.Frame(self.content,bg="#ffffff",padx=22,pady=22,highlightthickness=1,highlightbackground="#e3e9ef");panel2.pack(fill="x",pady=(0,16))
        tk.Label(panel2,text="ورود اطلاعات اشخاص از CSV",bg="#ffffff",fg="#14243d",font=("Tahoma",12,"bold"),anchor="e").pack(fill="x",pady=(0,8))
        tk.Label(panel2,text="ستون‌های قابل شناسایی: display_name / نام / name ، phone / تلفن / موبایل ، national_id / کد ملی. ردیف‌های متعارض برای بررسی دستی علامت می‌خورند.",bg="#ffffff",fg="#64748b",font=("Tahoma",9),anchor="e",justify="right",wraplength=850).pack(fill="x",pady=(0,10))
        ttk.Button(panel2,text="انتخاب CSV و پیش‌نمایش",style="Primary.TButton",command=self.import_parties_csv).pack(anchor="e")
        panel3=tk.Frame(self.content,bg="#ffffff",padx=22,pady=22,highlightthickness=1,highlightbackground="#e3e9ef");panel3.pack(fill="x")
        tk.Label(panel3,text="پشتیبان‌گیری",bg="#ffffff",fg="#14243d",font=("Tahoma",12,"bold"),anchor="e").pack(fill="x",pady=(0,8))
        tk.Label(panel3,text="فایل SQLite شامل اطلاعات عملیاتی و سوابق تغییرات است. پیش از جایگزینی یا انتقال پایگاه داده، برنامه را ببندید.",bg="#ffffff",fg="#64748b",font=("Tahoma",9),anchor="e",justify="right").pack(fill="x",pady=(0,10))
        ttk.Button(panel3,text="تهیه نسخه پشتیبان",command=self.backup_db).pack(anchor="e")

    def export_csv(self, entity):
        path=filedialog.asksaveasfilename(title="ذخیره خروجی CSV",defaultextension=".csv",filetypes=[("CSV","*.csv")],initialfile="sorting_os_%s_%s.csv"%(entity,date.today().isoformat()))
        if not path:return
        try:
            rows=self.db.export_rows(entity)
            with open(path,"w",encoding="utf-8-sig",newline="") as f:
                writer=csv.writer(f);writer.writerows(rows)
            self.status_var.set("خروجی ذخیره شد: "+os.path.basename(path));messagebox.showinfo("خروجی موفق","%d ردیف در فایل ذخیره شد."%(len(rows)-1),parent=self)
        except Exception as exc:messagebox.showerror("خروجی ناموفق",str(exc),parent=self)

    def import_parties_csv(self):
        path=filedialog.askopenfilename(title="انتخاب فایل اشخاص",filetypes=[("CSV","*.csv"),("همه فایل‌ها","*.*")])
        if not path:return
        try:
            with open(path,"r",encoding="utf-8-sig",newline="") as f:
                sample=f.read(2048);f.seek(0)
                try:dialect=csv.Sniffer().sniff(sample,delimiters=",;\t")
                except csv.Error:dialect=csv.excel
                reader=csv.DictReader(f,dialect=dialect);rows=list(reader)
            preview=self.db.import_parties_preview(rows)
            self._show_import_preview(path,preview)
        except UnicodeDecodeError:
            try:
                with open(path,"r",encoding="cp1256",newline="") as f:rows=list(csv.DictReader(f,delimiter=","))
                self._show_import_preview(path,self.db.import_parties_preview(rows))
            except Exception as exc:messagebox.showerror("خواندن فایل ناموفق",str(exc),parent=self)
        except Exception as exc:messagebox.showerror("خواندن فایل ناموفق",str(exc),parent=self)

    def _show_import_preview(self,path,items):
        win=tk.Toplevel(self);win.title("پیش‌نمایش ورود اشخاص");win.geometry("900x540");win.transient(self)
        tk.Label(win,text="پیش‌نمایش؛ قبل از نوشتن در پایگاه داده",font=("Tahoma",13,"bold"),anchor="e").pack(fill="x",padx=16,pady=14)
        tree=self._tree(win,("row","name","phone","nid","action","reason"),[("row","ردیف",50),("name","نام",180),("phone","تلفن",120),("nid","کد ملی",120),("action","تصمیم پیشنهادی",110),("reason","علت",300)],height=13)
        for it in items:tree.insert("","end",values=(it["row"],it["display_name"],it["phone"],it["national_id"],{"insert":"افزودن پس از تأیید","review":"بررسی دستی","skip":"رد ردیف"}[it["action"]],it["reason"]))
        inserts=sum(1 for x in items if x["action"]=="insert");reviews=sum(1 for x in items if x["action"]=="review")
        tk.Label(win,text="قابل افزودن: %d   |   نیازمند بررسی دستی: %d   |   بدون نام: %d"%(inserts,reviews,len(items)-inserts-reviews),font=("Tahoma",9),anchor="e").pack(fill="x",padx=16,pady=8)
        def import_safe():
            if not messagebox.askyesno("تأیید ورود","فقط ردیف‌های بدون تعارض اضافه شوند؟ ردیف‌های مشابه/متعارض وارد نمی‌شوند.",parent=win):return
            ok=0;errors=[]
            for it in items:
                if it["action"]!="insert":continue
                try:self.db.import_new_party(it);ok+=1
                except Exception as exc:errors.append("ردیف %s: %s"%(it["row"],exc))
            win.destroy();self.status_var.set("ورود CSV انجام شد: %d شخص جدید"%ok)
            if self.current_page=="parties":self._refresh_parties()
            message="%d شخص اضافه شد. %d ردیف به‌دلیل شباهت/تعارض وارد نشد."%(ok,len(items)-ok)
            if errors:message+="\n\n"+"\n".join(errors[:5])
            messagebox.showinfo("نتیجه ورود",message,parent=self)
        buttons=tk.Frame(win);buttons.pack(fill="x",padx=16,pady=10);ttk.Button(buttons,text="افزودن ردیف‌های بدون تعارض",command=import_safe).pack(side="right");ttk.Button(buttons,text="لغو",command=win.destroy).pack(side="right",padx=8)

    def backup_db(self):
        path=filedialog.asksaveasfilename(title="ذخیره نسخه پشتیبان",defaultextension=".sqlite3",filetypes=[("SQLite database","*.sqlite3"),("همه فایل‌ها","*.*")],initialfile="sorting_os_backup_%s.sqlite3"%datetime.now().strftime("%Y%m%d_%H%M"))
        if not path:return
        try:
            with self.db.connect() as source, __import__("sqlite3").connect(path) as target:
                source.backup(target)
            self.db.audit(ACTOR,"backup","database",None,os.path.basename(path))
            self.status_var.set("نسخه پشتیبان ساخته شد");messagebox.showinfo("پشتیبان موفق","نسخه پشتیبان ذخیره شد:\n"+path,parent=self)
        except Exception as exc:messagebox.showerror("پشتیبان ناموفق",str(exc),parent=self)

    def show_audit(self):
        self._clear();self.current_page="audit";self._heading("سوابق تغییرات", "ثبت محلی رویدادهای اصلی برای رهگیری عملیات؛ این فهرست جایگزین سامانه ممیزی مستقل سازمانی نیست.")
        tree=self._tree(self.content,("id","date","actor","action","entity","entity_id","details"),[("id","ID",50),("date","زمان",170),("actor","کاربر",130),("action","عملیات",90),("entity","نوع موجودیت",140),("entity_id","شناسه",70),("details","جزئیات",350)],height=18)
        for row in self.db.list_audit(300):tree.insert("","end",values=(row["id"],row["event_at"],row["actor"],row["action"],row["entity_type"],row["entity_id"] or "",row["details"] or ""))


def main():
    app=SortingApp()
    app.mainloop()

if __name__=="__main__": main()
