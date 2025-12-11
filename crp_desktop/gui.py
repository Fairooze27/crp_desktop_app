
import json
import time
import csv
import threading
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QLineEdit, QTextEdit, QMessageBox, QFormLayout,
    QFileDialog, QDateEdit, QHeaderView, QComboBox, QTabWidget
)
from PySide6.QtCore import QDate
import serial.tools.list_ports

from crp_desktop.db import get_db, get_settings, set_settings
from crp_desktop.serial_reader import read_serial_and_store_results
from crp_desktop.resources import BAUD_RATES
from crp_desktop import signals as signals_mod
from PySide6.QtWidgets import QMainWindow

from crp_desktop.report import generate_report_html, save_html_to_pdf

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.win = QMainWindow()
        self.win.setWindowTitle("CRP Desktop (PySide6) - Packaged")
        self.win.resize(1000, 700)

        self.conn = get_db()
        self.stop_event = threading.Event()
        self.listener_thread = None

        tabs = QTabWidget()
        tabs.addTab(self.make_home_tab(), "Home (Today)")
        tabs.addTab(self.make_results_tab(), "Results")
        tabs.addTab(self.make_settings_tab(), "Settings")
        tabs.addTab(self.make_serial_tab(), "Serial Monitor")
        self.win.setCentralWidget(tabs)

        if signals_mod.signals:
            signals_mod.signals.new_result.connect(self.on_new_result)
            signals_mod.signals.status.connect(self.on_status)

        self.load_today_results()
        self.search_results(load_all=True)  

    # --- Home
    def make_home_tab(self):
        w = QWidget()
        v = QVBoxLayout()
        hdr = QLabel("<b>Today's results</b>")
        v.addWidget(hdr)
        # columns: ID, Name, Date, Time, Instrument, key labs + hidden DB id
        self.table_today = QTableWidget(0, 11)
        self.table_today.setHorizontalHeaderLabels([
            "ID", "Name", "Date", "Time", "Instrument", "WBC", "RBC", "HGB", "PLT", "CRP", "DB_ID"
        ])
        self.table_today.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_today.setColumnHidden(10, True)
        v.addWidget(self.table_today)
        # detail box shows full payload of selected row
        self.today_detail = QTextEdit()
        self.today_detail.setReadOnly(True)
        self.today_detail.setPlaceholderText("Select a row to see full details")
        v.addWidget(self.today_detail)

        # selection handler
        self.table_today.itemSelectionChanged.connect(self.on_today_row_selected)
        btns = QHBoxLayout()
        export = QPushButton("Export CSV (Today)")
        export.clicked.connect(self.export_today)
        btns.addWidget(export)
        print_btn = QPushButton("Print selected (Today)")
        print_btn.clicked.connect(lambda: self.export_selected_report(from_today=True))
        btns.addWidget(print_btn)
        v.addLayout(btns)
        w.setLayout(v)
        return w

    def load_today_results(self):
        today = date.today().strftime("%Y-%m-%d")
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM crp_results "
            "WHERE date(COALESCE(measure_datetime, created_at)) = ? "
            "ORDER BY COALESCE(measure_datetime, created_at) DESC",
            (today,)
        )
        rows = cur.fetchall()
        self.table_today.setRowCount(0)
        for r in rows:
            rowpos = self.table_today.rowCount()
            self.table_today.insertRow(rowpos)
            name = ""
            try:
                raw = r["raw_payload"]
                if raw:
                    parsed_raw = json.loads(raw)
                    name = parsed_raw.get("NAME") or parsed_raw.get("Name") or parsed_raw.get("PatientName") or parsed_raw.get("PATIENT") or ""
            except Exception:
                name = ""
            pid = str(r["patient_id"] or "")
            dt = str(r["date"] or "")
            tm = str(r["time"] or "")
            instrument = str(r["instrument_no"] or r["instrument_name"] or "")
            self.table_today.setItem(rowpos, 0, QTableWidgetItem(pid))
            self.table_today.setItem(rowpos, 1, QTableWidgetItem(name))
            self.table_today.setItem(rowpos, 2, QTableWidgetItem(dt))
            self.table_today.setItem(rowpos, 3, QTableWidgetItem(tm))
            self.table_today.setItem(rowpos, 4, QTableWidgetItem(instrument))
            self.table_today.setItem(rowpos, 5, QTableWidgetItem(str(r["wbc"] or "")))
            self.table_today.setItem(rowpos, 6, QTableWidgetItem(str(r["rbc"] or "")))
            self.table_today.setItem(rowpos, 7, QTableWidgetItem(str(r["hgb"] or "")))
            self.table_today.setItem(rowpos, 8, QTableWidgetItem(str(r["plt"] or "")))
            self.table_today.setItem(rowpos, 9, QTableWidgetItem(str(r["crp"] or "")))
            # hidden id column used for printing/detail lookup
            self.table_today.setItem(rowpos, 10, QTableWidgetItem(str(r["id"])))

    def export_today(self):
        path, _ = QFileDialog.getSaveFileName(self.win, "Save today CSV", "today_results.csv", "CSV files (*.csv)")
        if not path:
            return
        today = date.today().strftime("%Y-%m-%d")
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM crp_results "
            "WHERE date(COALESCE(measure_datetime, created_at)) = ? "
            "ORDER BY COALESCE(measure_datetime, created_at) DESC",
            (today,)
        )
        rows = cur.fetchall()
        headers = [d[0] for d in cur.description]
        try:
            with open(path, "w", encoding="utf-8", newline='') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)
                for r in rows:
                    writer.writerow([r[h] if r[h] is not None else "" for h in headers])
            QMessageBox.information(self.win, "Export", f"Saved {len(rows)} rows to {path}")
        except Exception as e:
            QMessageBox.critical(self.win, "Export Error", str(e))

    # --- Results tab
    def make_results_tab(self):
        w = QWidget()
        v = QVBoxLayout()
        form = QHBoxLayout()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        self.patient_filter = QLineEdit()
        self.instrument_filter = QLineEdit()
        form.addWidget(QLabel("Start"))
        form.addWidget(self.start_date)
        form.addWidget(QLabel("End"))
        form.addWidget(self.end_date)
        form.addWidget(QLabel("Patient ID"))
        form.addWidget(self.patient_filter)
        form.addWidget(QLabel("Instrument"))
        form.addWidget(self.instrument_filter)
        search = QPushButton("Search")
        search.clicked.connect(self.search_results)
        form.addWidget(search)
        v.addLayout(form)
        self.table_results = QTableWidget(0, 10)
        self.table_results.setHorizontalHeaderLabels(["ID", "DateTime", "Patient", "Instrument", "WBC", "RBC", "HGB", "PLT", "CRP", "Raw"])
        self.table_results.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        v.addWidget(self.table_results)
        w.setLayout(v)
        return w

    def search_results(self , load_all=False):
        s = self.start_date.date().toString("yyyy-MM-dd")
        e = self.end_date.date().toString("yyyy-MM-dd")
        pid = self.patient_filter.text().strip()
        inst = self.instrument_filter.text().strip()
        query = "SELECT * FROM crp_results WHERE 1=1"
        params = []
        if not load_all:  # Only filter when Search button is pressed
            if s:
                query += " AND date(COALESCE(measure_datetime, created_at)) >= ?"
                params.append(s)
            if e:
                query += " AND date(COALESCE(measure_datetime, created_at)) <= ?"
                params.append(e)
            if pid:
                query += " AND patient_id LIKE ?"
                params.append(f"%{pid}%")
            if inst:
                query += " AND instrument_no LIKE ?"
                params.append(f"%{inst}%")


        query += " ORDER BY COALESCE(measure_datetime, created_at) DESC"
        cur = self.conn.cursor()
        cur.execute(query, params)
        rows = cur.fetchall()
        self.table_results.setRowCount(0)
        for r in rows:
            rowpos = self.table_results.rowCount()
            self.table_results.insertRow(rowpos)
            dt = r["measure_datetime"] or r["created_at"]
            self.table_results.setItem(rowpos, 0, QTableWidgetItem(str(r["id"])))
            self.table_results.setItem(rowpos, 1, QTableWidgetItem(str(dt)))
            self.table_results.setItem(rowpos, 2, QTableWidgetItem(str(r["patient_id"] or "")))
            self.table_results.setItem(rowpos, 3, QTableWidgetItem(str(r["instrument_no"] or "")))
            self.table_results.setItem(rowpos, 4, QTableWidgetItem(str(r["wbc"] or "")))
            self.table_results.setItem(rowpos, 5, QTableWidgetItem(str(r["rbc"] or "")))
            self.table_results.setItem(rowpos, 6, QTableWidgetItem(str(r["hgb"] or "")))
            self.table_results.setItem(rowpos, 7, QTableWidgetItem(str(r["plt"] or "")))
            self.table_results.setItem(rowpos, 8, QTableWidgetItem(str(r["crp"] or "")))
            self.table_results.setItem(rowpos, 9, QTableWidgetItem(str(r["raw_payload"] or "")))

    # --- Settings tab
    def make_settings_tab(self):
        w = QWidget()
        v = QVBoxLayout()
        form = QFormLayout()
        self.input_clinic = QLineEdit()
        self.input_report_title = QLineEdit()
        self.input_footer = QLineEdit()
        s = get_settings(self.conn)
        self.input_clinic.setText(s.get("clinic_name", ""))
        self.input_report_title.setText(s.get("report_title", ""))
        self.input_footer.setText(s.get("footer_text", ""))
        form.addRow("Clinic name", self.input_clinic)
        form.addRow("Report title", self.input_report_title)
        form.addRow("Footer", self.input_footer)
        v.addLayout(form)
        btn = QPushButton("Save settings")
        btn.clicked.connect(self.save_settings_clicked)
        v.addWidget(btn)
        w.setLayout(v)
        return w

    def save_settings_clicked(self):
        data = {
            "clinic_name": self.input_clinic.text().strip(),
            "report_title": self.input_report_title.text().strip(),
            "footer_text": self.input_footer.text().strip(),
        }
        set_settings(data, self.conn)
        QMessageBox.information(self.win, "Settings", "Saved settings.")

    # --- Serial Monitor tab
    def make_serial_tab(self):
        w = QWidget()
        v = QVBoxLayout()
        h = QHBoxLayout()
        self.cmb_ports = QComboBox()
        self.cmb_baud = QComboBox()
        for b in BAUD_RATES:
            self.cmb_baud.addItem(str(b))
        self.cmb_baud.setCurrentIndex(0)
        self.btn_refresh = QPushButton("Refresh ports")
        self.btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_start = QPushButton("Start listener")
        self.btn_start.clicked.connect(self.toggle_listener)
        h.addWidget(QLabel("Port:"))
        h.addWidget(self.cmb_ports)
        h.addWidget(QLabel("Baud:"))
        h.addWidget(self.cmb_baud)
        h.addWidget(self.btn_refresh)
        h.addWidget(self.btn_start)
        v.addLayout(h)
        self.lbl_status = QLabel("Status: idle")
        v.addWidget(self.lbl_status)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        v.addWidget(self.txt_log)
        self.refresh_ports()
        w.setLayout(v)
        return w
    
# COMPORTS
    def refresh_ports(self):
        self.cmb_ports.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.cmb_ports.addItem(p.device)
        if self.cmb_ports.count() == 0:
            self.cmb_ports.addItem("No ports found")

    def toggle_listener(self):
        if self.listener_thread and self.listener_thread.is_alive():
            self.stop_event.set()
            self.btn_start.setEnabled(False)
            self.lbl_status.setText("Stopping listener...")
        else:
            port_name = self.cmb_ports.currentText()
            if not port_name or port_name == "No ports found":
                QMessageBox.warning(self.win, "No port", "Please select a valid COM port.")
                return
            try:
                baud = int(self.cmb_baud.currentText())
            except Exception:
                baud = int(self.cmb_baud.itemText(0))
            self.stop_event.clear()
            self.listener_thread = threading.Thread(
                target=read_serial_and_store_results,
                args=(self.stop_event, port_name, baud),
                daemon=True
            )
            self.listener_thread.start()
            self.btn_start.setText("Stop listener")
            self.lbl_status.setText(f"Listener running on {port_name}@{baud}")
            self.txt_log.append(f"Started listener on {port_name}@{baud}")

    def on_new_result(self, parsed):
        self.load_today_results()
        self.search_results()
        self.txt_log.append("New result: " + str(parsed.get("ID", "<no id>")))

    def on_status(self, msg):
        self.txt_log.append(msg)
        self.lbl_status.setText(msg)
        if "stopped" in msg.lower() or "error" in msg.lower():
            self.btn_start.setText("Start listener")
            self.btn_start.setEnabled(True)

    def show(self):
        self.win.show()

    def close(self):
        self.stop_event.set()
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1.0)
        try:
            self.conn.close()
        except Exception:
            pass

    def on_today_row_selected(self):
        """
        When a row is selected on the Home tab, show full details below.
        """
        sel = self.table_today.currentRow()
        if sel is None or sel < 0:
            self.today_detail.clear()
            return
        id_item = self.table_today.item(sel, 10)  # hidden DB id
        if not id_item or not id_item.text():
            self.today_detail.clear()
            return
        try:
            row_id = int(id_item.text())
        except Exception:
            self.today_detail.clear()
            return

        cur = self.conn.cursor()
        cur.execute("SELECT * FROM crp_results WHERE id = ?", (row_id,))
        r = cur.fetchone()
        if not r:
            self.today_detail.clear()
            return

        # Build a readable detail block
        detail_lines = []
        detail_lines.append(f"Patient ID: {r['patient_id'] or ''}")
        detail_lines.append(f"Name: {self.table_today.item(sel, 1).text() if self.table_today.item(sel, 1) else ''}")
        dt_full = r["measure_datetime"] or f"{r['date'] or ''} {r['time'] or ''}".strip()
        detail_lines.append(f"Date/Time: {dt_full}")
        detail_lines.append(f"Instrument: {r['instrument_no'] or r['instrument_name'] or ''}")
        detail_lines.append("")
        for key in ["wbc", "rbc", "hgb", "hct", "mcv", "mch", "mchc", "rdw", "plt", "mpv", "pct", "pdw", "crp"]:
            detail_lines.append(f"{key.upper()}: {r[key] or ''}")

        # show raw payload (pretty json) if present
        raw = r["raw_payload"]
        if raw:
            try:
                parsed_raw = json.loads(raw)
                detail_lines.append("\nRaw payload:")
                detail_lines.append(json.dumps(parsed_raw, indent=2, ensure_ascii=False))
            except Exception:
                detail_lines.append("\nRaw payload:")
                detail_lines.append(str(raw))

        self.today_detail.setPlainText("\n".join(detail_lines))


    def export_selected_report(self, from_today: bool = False):
        """
        Print/Save a PDF for the selected row.
        - from_today=True: uses the Home tab table (today's results)
        - otherwise: uses the Results tab table (full search)
        """
        table = self.table_today if from_today else self.table_results
        id_col = 10 if from_today else 0  # hidden DB id on home tab, visible id on results tab

        sel = table.currentRow()
        if sel is None or sel < 0:
            QMessageBox.warning(self.win, "Select row", "Please select a result row to print.")
            return
        row_id_item = table.item(sel, id_col)
        if not row_id_item or not row_id_item.text():
            QMessageBox.warning(self.win, "Select row", "Please select a valid result row.")
            return
        try:
            row_id = int(row_id_item.text())
        except Exception:
            QMessageBox.warning(self.win, "Select row", "Could not read the selected row id.")
            return
    
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM crp_results WHERE id = ?", (row_id,))
        r = cur.fetchone()
        if not r:
            QMessageBox.critical(self.win, "Error", "Could not find result in database.")
            return
    
        parsed = dict(r)  # row access; parsed info in raw_payload too
        try:
            raw = parsed.get("raw_payload")
            if raw:
                try:
                    parsed_from_raw = json.loads(raw)
                    # prefer parsed_from_raw for display (contains parsed field names)
                    parsed.update(parsed_from_raw)
                except Exception:
                    pass
        except Exception:
            pass
        
        settings = get_settings(self.conn)
        # optional: pass path of logo from settings: settings.get("logo_path")
        html = generate_report_html(parsed, settings, logo_path=settings.get("logo_path"))
        path, _ = QFileDialog.getSaveFileName(self.win, "Save PDF", "report.pdf", "PDF Files (*.pdf)")
        if not path:
            return
        try:
            save_html_to_pdf(html, path)
            QMessageBox.information(self.win, "Saved", f"Saved report to {path}")
        except Exception as e:
            QMessageBox.critical(self.win, "Error", str(e))
    