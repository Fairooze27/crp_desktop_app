✅ CRP Desktop – Medical Device Data Acquisition & Reporting System

A production-grade PySide6 desktop application for CBC/CRP medical analyzers.

📌 Overview

CRP Desktop is a standalone Windows desktop application built for clinics and laboratories to:

Receive real-time CBC/CRP data from medical analyzers via RS232 serial communication

Automatically parse & store measurements in a local SQLite database

Provide a clean GUI for viewing today’s results, historical data, and live serial monitoring

Export data to CSV

Configure clinic details and reporting preferences

Run fully offline, with no internet required

This project demonstrates full-stack desktop engineering with:

PySide6 (Qt)

RS232 communication (pyserial)

Multithreading

SQLite storage

PyInstaller + Inno Setup packaging

✨ Key Features
🩺 Medical Data Acquisition

Reads RS232 output from CRP/CBC analyzers

Multithreaded listener keeps UI responsive

Real-time parsing of WBC, RBC, HGB, PLT, CRP, timestamps & raw payloads

📊 Results Dashboard

Home tab → Today’s test results

Results tab → Full database with filtering:

Date range

Patient ID

Instrument number

CSV export

💾 Local Data Storage

SQLite-based database

Auto-creation of tables on first run

All results stored offline

🔌 Serial Monitor

COM port detection

Option to display all COM ports (COM1–COM256)

Live logs of incoming serial data

⚙️ App Settings

Clinic name

Report titles

Footer text

All saved to persistent SQLite settings table

🏁 Windows Installer

Built using PyInstaller + Inno Setup

Creates:

Desktop shortcut

Start Menu entry

Uninstaller

Fully standalone .exe — no Python needed

🛠️ Tech Stack
Layer	Technology
GUI	PySide6 (Qt)
Serial I/O	pyserial
Storage	SQLite
Concurrency	Python threading
Packaging	PyInstaller
Installer	Inno Setup
OS	Windows

▶️ Running the App (Development)
1. Create & activate virtual environment
python -m venv venv
source venv/Scripts/activate

2. Install dependencies
pip install -r requirements.txt

3. Run locally
python -m crp_desktop.main
