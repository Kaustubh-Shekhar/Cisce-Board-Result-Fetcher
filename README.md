# CISCE Result Checker 🎓

An automated Python script that checks your ICSE/ISC results on [results.cisce.org](https://results.cisce.org/) the moment they go live — so you don't have to sit refreshing all day.

---

## ✨ Features

- 🔁 **Loops forever** — start it before results are out, it keeps trying until it gets them
- ⚡ **10 parallel tabs** — runs 10 browser tabs simultaneously for maximum speed
- 🤖 **Auto CAPTCHA solving** — uses EasyOCR locally (no paid API needed)
- 📸 **Full-page screenshot** — saves the entire result page the moment it loads
- 🛑 **Auto-stops** — all tabs shut down as soon as any one of them succeeds
- 🔄 **Smart retry** — handles site crashes, wrong CAPTCHAs, and timeouts gracefully

---

## 📋 Requirements

- Python 3.8+
- Windows / macOS / Linux

---

## 🚀 Setup

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/cisce-result-checker.git
cd cisce-result-checker
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Edit your details in `cisce_form.py`
Open the file and fill in your info in the config block at the top:

```python
CENTER_CODE   = "YOUR_CENTER_CODE"    # Index No First Part
SERIAL_NO     = "YOUR_SERIAL_NUMBER"  # INDEX NO. second Part
UNIQUE_ID     = "YOUR_UNIQUE_ID"      # UID field
COURSE        = "ICSE"                # or "ISC"
```

You can find these on your CISCE admit card.

### 4. Run
```bash
python cisce_form.py
```

---

## 📁 Output

Screenshots are saved automatically to your Desktop in a folder called `CISCE_Results`:

```
Desktop/
└── CISCE_Results/
    └── RESULT_tab3_143022.png  ← full-page result screenshot
```

---

## ⚙️ Configuration Options

| Option | Default | Description |
|---|---|---|
| `NUM_TABS` | `10` | Number of parallel browser tabs |
| `RETRY_DELAY` | `5` | Seconds to wait between retries |
| `HEADLESS` | `False` | Set `True` to hide the browser window |
| `SCREENSHOT_DIR` | Desktop/CISCE_Results | Where to save screenshots |

---

## 🔧 How it works

```
Start script
    └── Launch 10 browser tabs simultaneously
            └── Each tab independently:
                    1. Opens results.cisce.org
                    2. Selects ICSE from dropdown
                    3. Fills UID and Index No.
                    4. Screenshots & OCRs the CAPTCHA
                    5. Submits the form
                    6. Checks if result loaded
                        ├── ✅ Success → saves screenshot, stops all tabs
                        ├── ❌ Wrong CAPTCHA → retries immediately
                        └── ⚠️  Site down / error → waits 5s, retries
```

---

## ⚠️ Disclaimer

This script is intended for **personal use only** — to check your own CISCE exam results. The author is not responsible for any misuse. Use responsibly and in accordance with CISCE's terms of service.

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `playwright` | Browser automation |
| `easyocr` | CAPTCHA text recognition |
| `opencv-python-headless` | Image preprocessing |
| `Pillow` | Image manipulation |

---

## 🤝 Contributing

PRs welcome! If the CAPTCHA selector or form field IDs change after a site update, feel free to open an issue or submit a fix.

---

## 📄 License

MIT License — free to use, modify, and distribute.
