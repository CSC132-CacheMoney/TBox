<div align="center">

# 🧰 ToolVault
### RFID-Powered Toolbox Inventory & Checkout System

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![HTML/CSS](https://img.shields.io/badge/GUI-HTML%20%2F%20CSS-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![RFID](https://img.shields.io/badge/Hardware-RFID-00C853?style=for-the-badge&logo=nfc&logoColor=white)]()
[![License](https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge)](https://www.apache.org/licenses/LICENSE-2.0)

*A smart, hardware-integrated tool management system built for CSC-132 Freshman Design Expo*

---

**Team Cache Money** &nbsp;|&nbsp; Loki · JB · Jaden · Aidan

</div>

---

## 📖 Overview

**ToolVault** is an RFID-powered toolbox inventory and checkout system that eliminates the headache of lost or unreturned tools. Each tool is tagged with an RFID sticker and tracked in real time. When a tool is checked out, a configurable timer begins — and if it isn't returned in time, ToolVault fires an alert so nothing goes missing for long.

The system pairs a Python backend with a clean HTML/CSS web GUI, allowing users to register new tools, check them in and out, retire old ones, and browse the full inventory at a glance — all without ever touching a spreadsheet.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📡 **RFID Scanning** | Scan RFID stickers attached to tools for instant identification |
| ⏱️ **Overdue Alerts** | Configurable checkout time limit — get notified when tools aren't returned |
| 🗂️ **Full Inventory View** | Browse every tool, its status, and its checkout history |
| ✅ **Checkout & Check-in** | Seamlessly log when tools leave and return |
| 🔧 **Tool Registration** | Add new tools to the system by scanning their RFID tag |
| 🗑️ **Tool Retirement** | Mark tools as retired/out-of-service when they're no longer usable |
| 🖥️ **Web-Based GUI** | Intuitive HTML/CSS interface — no installation required for the front end |
| ⚙️ **Configurable Settings** | Adjust alert thresholds and system preferences through the GUI |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                        GUI Layer                        │
│              (HTML / CSS — Browser-Based)               │
│   Inventory View · Checkout · Registration · Retire     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / Local API
┌────────────────────────▼────────────────────────────────┐
│                    Python Backend                       │
│         Flask/FastAPI · Business Logic · Alerts         │
│         Checkout Timer · Configuration Manager          │
└────────────────────────┬────────────────────────────────┘
                         │ Serial / GPIO
┌────────────────────────▼────────────────────────────────┐
│                   Hardware Layer                        │
│              RFID Reader · RFID Tag Stickers            │
└─────────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Data Storage                         │
│              SQLite Database (tools.db)                 │
│        Tools · Checkouts · Users · Config               │
└─────────────────────────────────────────────────────────┘
```

---

## 🗂️ Project Structure

```
ToolVault/
├── backend/
│   ├── main.py               # Application entry point
│   ├── rfid_reader.py        # RFID hardware interface
│   ├── inventory.py          # Inventory management logic
│   ├── checkout.py           # Checkout / check-in logic
│   ├── alerts.py             # Overdue alert system
│   ├── config.py             # Configuration manager
│   └── database.py           # SQLite database interface
│
├── gui/
│   ├── index.html            # Main dashboard / inventory view
│   ├── checkout.html         # Checkout & check-in page
│   ├── register.html         # Tool registration page
│   ├── retire.html           # Tool retirement page
│   ├── settings.html         # System configuration page
│   └── styles/
│       ├── main.css          # Global styles
│       └── components.css    # Reusable UI components
│
├── data/
│   └── tools.db              # SQLite database (auto-generated)
│
├── config/
│   └── settings.json         # Default configuration file
│
├── tests/
│   ├── test_inventory.py
│   ├── test_checkout.py
│   └── test_alerts.py
│
├── requirements.txt
└── README.md
```

---

## 🛠️ Hardware Requirements

- **RFID Reader** — RC522 or compatible module (SPI interface)
- **Microcontroller / SBC** — Raspberry Pi (recommended) or any device with GPIO/serial support
- **RFID Stickers / Tags** — 13.56 MHz MIFARE tags (one per tool)
- **Host Machine** — Any machine capable of running Python 3.10+

> **Note:** The GUI runs in any modern web browser, making it accessible from any device on the same network.

---

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/cache-money/toolvault.git
cd toolvault
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Hardware

Edit `config/settings.json` to match your RFID reader's connection details:

```json
{
  "rfid": {
    "port": "/dev/ttyUSB0",
    "baud_rate": 9600
  },
  "alerts": {
    "checkout_limit_minutes": 60,
    "alert_method": "console"
  },
  "database": {
    "path": "data/tools.db"
  }
}
```

### 4. Initialize the Database

```bash
python backend/database.py --init
```

### 5. Run the Application

```bash
python backend/main.py
```

Then open your browser and navigate to `http://localhost:5000` to access the GUI.

---

## 🖥️ GUI Pages

### 📋 Inventory Dashboard (`index.html`)
View all registered tools with their current status (Available, Checked Out, Retired), who has them, and how long they've been out.

### ✅ Checkout / Check-in (`checkout.html`)
Scan a tool's RFID tag to instantly check it out or return it. The system logs the timestamp and starts (or stops) the overdue timer automatically.

### ➕ Register Tool (`register.html`)
Add a new tool to the system by scanning its RFID sticker and entering details like tool name, category, and condition.

### 🗑️ Retire Tool (`retire.html`)
Mark a tool as retired/out-of-service. Retired tools are removed from active inventory but kept in the database for historical records.

### ⚙️ Settings (`settings.html`)
Configure the checkout time limit, alert preferences, and other system settings without touching the codebase.

---

## 🔔 Alert System

ToolVault monitors all active checkouts in the background. When a tool exceeds the configured checkout duration, an alert is triggered.

**Configurable options:**
- `checkout_limit_minutes` — How long a tool can be checked out before an alert fires
- `alert_method` — Where alerts are sent (`console`, `email`, or future integrations)

Alerts include the tool name, RFID tag ID, checkout time, and how overdue it is.

---

## 🧪 Running Tests

```bash
python -m pytest tests/
```

---

## 📋 Requirements

```
flask>=2.3.0
mfrc522>=0.0.7
RPi.GPIO>=0.7.1
sqlite3
pytest>=7.0.0
```

> See `requirements.txt` for the full dependency list.

---

## 👥 Team Cache Money

| Name | Role |
|---|---|
| **Loki** | Hardware Integration & RFID Interface |
| **JB** | Python Backend & Database Design |
| **Jaden** | GUI Design & Frontend Development |
| **Aidan** | Alert System & Configuration Logic |

*CSC-132 — Freshman Design Expo*

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

<div align="center">

*Built with 💸 by Cache Money*

</div>