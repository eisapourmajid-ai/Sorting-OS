# -*- coding: utf-8 -*-
"""Tkinter shell of SORTING OS (Prompt 24).

Design rules honoured by this module:

* the UI never contains accounting rules — every call goes to
  ``application.services``;
* the layout is right-to-left, all texts are Persian, and Latin/number tokens
  are bidi-isolated (see :mod:`sorting_os.ui.formatting`);
* every action runs inside an error boundary that logs the traceback locally
  and shows a Persian message instead of crashing the window;
* monetary fields always show the unit next to the value and the unit selector
  is independent from the display unit;
* the light/dark switch is local, stored in the settings table, and never
  touches business data.

``tkinter`` is imported lazily inside :func:`launch` so that the module can be
imported (and unit tested) on a machine without tkinter.  In that case the UI
is *not run* and no claim about the GUI can be made.
"""
from __future__ import annotations

from .formatting import (empty_state_text, isolate, isolate_tokens, money_display,
                         status_label, weight_display)
from .theme import ThemeService

APP_TITLE = "SORTING OS — سورتینگ و حسابداری"

NAV_ITEMS = (
    ("dashboard", "نمای کلی"),
    ("parties", "اشخاص"),
    ("shipments", "محموله و توزین"),
    ("sorting", "سورتینگ"),
    ("inventory", "انبار"),
    ("invoices", "فاکتور"),
    ("ledger", "دفترکل"),
    ("reports", "گزارش‌ها"),
    ("settings", "تنظیمات"),
)


class UiError(Exception):
    """Raised inside a guarded action to show a readable message."""


def _tk():
    """Import tkinter lazily and raise a readable error when unavailable."""
    try:
        import tkinter  # noqa: F401
        from tkinter import ttk  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on the machine
        raise UiError("محیط گرافیکی در دسترس نیست (tkinter نصب نیست): %s" % exc)
    return tkinter


class MainWindow:
    """The main window.  ``application`` is a :class:`sorting_os.app.Application`."""

    def __init__(self, application, root=None):
        self.app = application
        self.services = application.services
        self.logger = application.logger
        self.theme = ThemeService(application.db, actor=application.actor)
        self.theme.load()
        self.unsaved = False
        self._tk = _tk()
        self.root = root or self._tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1180x720")
        self.root.minsize(960, 600)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._build()
        self.apply_theme()

    # -- construction ------------------------------------------------------- #
    def _build(self):
        tk = self._tk
        from tkinter import ttk

        self.container = ttk.Frame(self.root, padding=0)
        self.container.pack(fill="both", expand=True)
        self.container.rowconfigure(1, weight=1)
        self.container.columnconfigure(0, weight=1)

        self._build_header(ttk)
        self._build_body(ttk)
        self._build_statusbar(ttk)

    def _build_header(self, ttk):
        self.header = ttk.Frame(self.container, padding=(12, 8))
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.columnconfigure(2, weight=1)

        self.title_label = ttk.Label(self.header, text="نمای کلی", anchor="e")
        self.title_label.grid(row=0, column=0, sticky="e", padx=(0, 12))

        self.search_var = tk.StringVar()
        self.search = ttk.Entry(self.header, textvariable=self.search_var, width=28)
        self.search.grid(row=0, column=1, sticky="e", padx=12)
        self.search_var.trace_add("write", lambda *_: self.refresh_current())

        self.status_label = ttk.Label(self.header, text="محلی · آماده", anchor="e")
        self.status_label.grid(row=0, column=2, sticky="e")

        self.theme_button = ttk.Button(self.header, text="تم: روشن",
                                       command=self.toggle_theme)
        self.theme_button.grid(row=0, column=3, sticky="e", padx=12)

        self.user_label = ttk.Label(self.header, text=self.app.actor, anchor="e")
        self.user_label.grid(row=0, column=4, sticky="e")

    def _build_body(self, ttk):
        from tkinter import ttk

        body = ttk.Frame(self.container, padding=12)
        body.grid(row=1, column=0, sticky="nsew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        self.sidebar = ttk.Frame(body, padding=(0, 0, 8, 0))
        self.sidebar.grid(row=0, column=0, sticky="nsw")

        self.notebook = ttk.Notebook(body)
        self.notebook.grid(row=0, column=1, sticky="nsew")
        self.tabs = {}
        self.screens = {}
        for key, label in NAV_ITEMS:
            frame = ttk.Frame(self.notebook, padding=10)
            self.notebook.add(frame, text=label)
            self.tabs[key] = frame
            self.screens[key] = self._build_screen(key, label, ttk, frame)

    def _build_statusbar(self, ttk):
        self.statusbar = ttk.Label(self.container, text="آماده", anchor="e",
                                   padding=(12, 4))
        self.statusbar.grid(row=2, column=0, sticky="ew")

    # -- screens ------------------------------------------------------------ #
    def _build_screen(self, key, label, ttk, frame):
        """Create a screen.  Each screen only *reads* through the services."""
        builder = {
            "dashboard": self._screen_dashboard,
            "parties": self._screen_parties,
            "shipments": self._screen_shipments,
            "sorting": self._screen_sorting,
            "inventory": self._screen_inventory,
            "invoices": self._screen_invoices,
            "ledger": self._screen_ledger,
            "reports": self._screen_reports,
            "settings": self._screen_settings,
        }.get(key)
        if builder is None:  # pragma: no cover - defensive
            return None
        return builder(ttk, frame)

    def _screen_dashboard(self, ttk, frame):
        self.dashboard_text = tk_text(ttk, frame, height=18)
        self.dashboard_text.pack(fill="both", expand=True)
        ttk.Button(frame, text="به‌روزرسانی", command=self.refresh_current).pack(
            anchor="e", pady=6)
        return {"refresh": self.refresh_dashboard}

    def _screen_parties(self, ttk, frame):
        self.parties_tree = tree(ttk, frame, ("id", "name", "roles", "phone"),
                                 ("شناسه", "نام", "نقش‌ها", "تلفن"))
        self.parties_tree.pack(fill="both", expand=True)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=6)
        name = tk_entry(ttk, row, 28)
        ttk.Label(row, text="نام", anchor="e").pack(side="right")
        name.pack(side="right", padx=4)
        ttk.Button(row, text="ثبت اشخاص", command=lambda: self.guard(
            lambda: self._create_party(name.get()))).pack(side="right", padx=4)
        return {"refresh": self.refresh_parties}

    def _screen_shipments(self, ttk, frame):
        self.shipments_tree = tree(ttk, frame, ("id", "owner", "weight", "date"),
                                   ("شناسه", "مالک", "وزن (کیلوگرم)", "تاریخ دریافت"))
        self.shipments_tree.pack(fill="both", expand=True)
        return {"refresh": self.refresh_shipments}

    def _screen_sorting(self, ttk, frame):
        self.sorting_tree = tree(ttk, frame, ("id", "shipment", "input", "output"),
                                 ("شناسه", "محموله", "ورودی (کیلوگرم)",
                                  "خروجی (کیلوگرم)"))
        self.sorting_tree.pack(fill="both", expand=True)
        return {"refresh": self.refresh_sorting}

    def _screen_inventory(self, ttk, frame):
        self.inventory_tree = tree(ttk, frame, ("location", "product", "balance"),
                                   ("انبار", "محصول", "موجودی (کیلوگرم)"))
        self.inventory_tree.pack(fill="both", expand=True)
        return {"refresh": self.refresh_inventory}

    def _screen_invoices(self, ttk, frame):
        self.invoices_tree = tree(ttk, frame, ("id", "code", "date", "amount", "status"),
                                  ("شناسه", "شماره", "تاریخ", "مبلغ (ریال)", "وضعیت"))
        self.invoices_tree.pack(fill="both", expand=True)
        return {"refresh": self.refresh_invoices}

    def _screen_ledger(self, ttk, frame):
        self.ledger_text = tk_text(ttk, frame, height=18)
        self.ledger_text.pack(fill="both", expand=True)
        return {"refresh": self.refresh_ledger}

    def _screen_reports(self, ttk, frame):
        self.reports_text = tk_text(ttk, frame, height=18)
        self.reports_text.pack(fill="both", expand=True)
        return {"refresh": self.refresh_reports}

    def _screen_settings(self, ttk, frame):
        self.settings_text = tk_text(ttk, frame, height=18)
        self.settings_text.pack(fill="both", expand=True)
        return {"refresh": self.refresh_settings}

    # -- data loading ------------------------------------------------------- #
    def refresh_current(self):
        key = self.current_key()
        screen = self.screens.get(key)
        if not screen:
            return
        try:
            screen["refresh"]()
        except Exception as exc:  # pragma: no cover - UI path
            self.logger.exception("خطا در تازه‌سازی صفحه %s", key)
            self.set_status("خطا در بارگذاری داده: %s" % exc)

    def current_key(self):
        try:
            index = self.notebook.index(self.notebook.select())
        except Exception:  # pragma: no cover - defensive
            return NAV_ITEMS[0][0]
        return NAV_ITEMS[index][0]

    def refresh_dashboard(self):
        dashboard = self.services.reporting.dashboard()
        commercial = dashboard.get("commercial", {})
        financial = dashboard.get("financial", {})
        lines = [
            "نمای کلی مجموعه (داده واقعی محلی)",
            "----------------------------------------",
            "فاکتورهای قطعی: %s" % commercial.get("confirmed_invoices", 0),
            "مبلغ فاکتورهای قطعی: %s" % money_display(
                commercial.get("confirmed_amount_rial", 0)),
            "مانده دریافتنی: %s" % money_display(financial.get("receivables_rial", 0)),
            "وزن ورودی امروز: %s" % weight_display(
                dashboard.get("operations", {}).get("received_weight_kg", 0)),
        ]
        self._set_text(self.dashboard_text, "\n".join(lines))

    def refresh_parties(self):
        rows = self.services.parties.list_all()
        self._fill_tree(self.parties_tree, [(p["id"], p["display_name"],
                                             "، ".join(p.get("roles") or []),
                                             p.get("phone") or "—")
                                            for p in rows],
                        empty_state_text("table"))

    def refresh_shipments(self):
        rows = self.services.operations.list_shipments()
        self._fill_tree(self.shipments_tree,
                        [(s["id"], s.get("owner_name") or s.get("owner_party_id") or "—",
                          "%.1f" % (s.get("received_weight_kg") or 0),
                          s.get("received_at") or "—") for s in rows],
                        empty_state_text("table"))

    def refresh_sorting(self):
        rows = self.services.operations.list_sorting_operations()
        self._fill_tree(self.sorting_tree,
                        [(o["id"], o.get("shipment_id"), "%.1f" % (o.get("input_weight_kg") or 0),
                          "%.1f" % (o.get("output_weight_kg") or 0)) for o in rows],
                        empty_state_text("table"))

    def refresh_inventory(self):
        balances = self.services.operations.inventory_balance()
        rows = balances.get("by_bucket", []) if isinstance(balances, dict) else []
        self._fill_tree(self.inventory_tree,
                        [(b.get("location_id"), b.get("product_id"),
                          "%.1f" % (b.get("balance_kg") or 0)) for b in rows],
                        empty_state_text("table"))

    def refresh_invoices(self):
        rows = self.services.documents.list_invoices()
        self._fill_tree(self.invoices_tree,
                        [(i["id"], i.get("code"), i.get("document_date"),
                          "{:,}".format(int(i.get("amount_rial") or 0)),
                          status_label(i.get("status"))) for i in rows],
                        empty_state_text("table"))

    def refresh_ledger(self):
        trial = self.services.ledger.book.trial_balance()
        lines = ["تراز آزمایشی (ریال)", "-------------------------------"]
        for account in trial.get("accounts", []):
            lines.append("%s %s بدهکار=%s بستانکار=%s مانده=%s" % (
                isolate(account.get("code")), account.get("name"),
                "{:,}".format(int(account.get("debit_rial") or 0)),
                "{:,}".format(int(account.get("credit_rial") or 0)),
                "{:,}".format(int(account.get("balance_rial") or 0))))
        lines.append("متوازن: %s" % ("بله" if trial.get("is_balanced") else "خیر"))
        self._set_text(self.ledger_text, "\n".join(lines))

    def refresh_reports(self):
        dashboard = self.services.reporting.dashboard()
        self._set_text(self.reports_text,
                       "گزارش‌ها از داده واقعی دفترکل ساخته می‌شوند.\n\n%s"
                       % dashboard.get("generated_at", ""))

    def refresh_settings(self):
        info = self.app.version_info()
        lines = [
            "نسخه: %s" % info["version"],
            "پایگاه داده: %s" % info["database"],
            "نسخهٔ schema: %s" % info["schema_version"],
            "تم: %s" % self.theme.mode,
            "",
            "تصمیم‌های باز (نیازمند تأیید کسب‌وکار):",
        ]
        lines.extend("• %s" % key for key in info.get("open_decisions", []))
        self._set_text(self.settings_text, "\n".join(lines))

    # -- actions ------------------------------------------------------------ #
    def _create_party(self, name):
        name = (name or "").strip()
        if not name:
            raise UiError("نام شخص را وارد کنید.")
        party = self.services.parties.create(name, actor=self.app.actor)
        self.set_status("شخص «%s» ثبت شد." % name)
        self.refresh_parties()
        return party

    def toggle_theme(self):
        try:
            mode = self.theme.toggle()
        except Exception as exc:  # pragma: no cover - UI path
            self.logger.exception("ذخیره تم ناموفق بود")
            self.set_status("ذخیره تم ناموفق بود: %s" % exc)
            return
        self.apply_theme()
        self.set_status("تم به «%s» تغییر کرد." % ("تیره" if mode == "dark" else "روشن"))

    def apply_theme(self):
        """Apply the token table to the standard widgets."""
        tokens = self.theme.tokens()
        try:
            from tkinter import ttk
            style = ttk.Style(self.root)
            style.theme_use("clam")
            style.configure(".", background=tokens["background"],
                            foreground=tokens["text"], fieldbackground=tokens["surface"])
            style.configure("TFrame", background=tokens["background"])
            style.configure("TLabel", background=tokens["background"],
                            foreground=tokens["text"])
            style.configure("TButton", background=tokens["surface_alt"],
                            foreground=tokens["text"])
            style.configure("Treeview", background=tokens["surface"],
                            fieldbackground=tokens["surface"],
                            foreground=tokens["text"])
            style.configure("Treeview.Heading", background=tokens["surface_alt"],
                            foreground=tokens["text"])
            self.root.configure(background=tokens["background"])
            self.header.configure(background=tokens["header_background"])
            self.theme_button.configure(text="تم: %s" % ("تیره" if self.theme.mode == "dark"
                                                           else "روشن"))
        except Exception:  # pragma: no cover - UI path
            self.logger.exception("اعمال تم ناموفق بود")

    # -- helpers ------------------------------------------------------------ #
    def guard(self, action):
        """Error boundary: log the traceback and show a Persian message."""
        try:
            return action()
        except Exception as exc:
            self.logger.exception("خطا در عملیات رابط کاربری")
            self.show_error(str(exc))
            return None

    def show_error(self, message):
        try:
            from tkinter import messagebox
            messagebox.showerror("خطا", message, parent=self.root)
        except Exception:  # pragma: no cover - UI path
            self.set_status("خطا: %s" % message)

    def set_status(self, message):
        try:
            self.statusbar.configure(text=message)
        except Exception:  # pragma: no cover - UI path
            pass

    def _set_text(self, widget, text):
        try:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", text)
            widget.configure(state="disabled")
        except Exception:  # pragma: no cover - UI path
            pass

    def _fill_tree(self, tree, rows, empty_text):
        try:
            tree.delete(*tree.get_children())
        except Exception:  # pragma: no cover - UI path
            pass
        if not rows:
            try:
                tree.insert("", "end", values=("", empty_text, "", ""))
            except Exception:  # pragma: no cover - UI path
                pass
            return
        for row in rows:
            try:
                tree.insert("", "end", values=row)
            except Exception:  # pragma: no cover - UI path
                pass

    # -- lifecycle ---------------------------------------------------------- #
    def on_close(self):
        if self.unsaved:
            from tkinter import messagebox
            answer = messagebox.askyesnocancel(
                "تغییرات ذخیره‌نشده",
                "فرم دارای تغییرات ذخیره‌نشده است. ذخیره شود؟",
                parent=self.root)
            if answer is None:
                return
            if answer is False:
                self.unsaved = False
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# -- small widget helpers (kept free of tkinter imports at module level) --- #
def tree(ttk, parent, columns, headings):
    widget = ttk.Treeview(parent, columns=list(columns), show="headings")
    for column, heading in zip(columns, headings):
        widget.heading(column, text=heading)
        widget.column(column, width=180, anchor="e")
    return widget


def tk_text(ttk, parent, height=12):
    from tkinter import scrolledtext
    return scrolledtext.ScrolledText(parent, height=height, wrap="word",
                                     font=("Tahoma", 10))


def tk_entry(ttk, parent, width=24):
    from tkinter import ttk
    return ttk.Entry(parent, width=width)


def launch(application):
    """Start the graphical shell.  Requires a working tkinter installation."""
    window = MainWindow(application)
    window.refresh_current()
    window.run()
    return 0
