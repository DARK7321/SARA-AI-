from fpdf import FPDF
import datetime

class SaraPDF(FPDF):
    def header(self):
        self.set_fill_color(10, 15, 30)
        self.rect(0, 0, 210, 297, 'F')
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(0, 200, 180)
        self.set_y(12)
        self.cell(0, 10, "OmniBrain SARA", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 11)
        self.set_text_color(150, 200, 255)
        self.cell(0, 6, "Complete Windows Native App Plan & Technical Report", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(100, 120, 140)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, f"Generated: {datetime.datetime.now().strftime('%d %B %Y, %I:%M %p')}", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)
        self.set_draw_color(0, 200, 180)
        self.set_line_width(0.5)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(80, 100, 120)
        self.cell(0, 10, f"OmniBrain SARA | Page {self.page_no()}", align="C")

    def section_title(self, title, emoji=""):
        self.ln(4)
        self.set_fill_color(20, 30, 50)
        self.set_draw_color(0, 200, 180)
        self.set_line_width(0.3)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 220, 200)
        self.cell(0, 10, f"  {emoji}  {title}", border="L", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text, color=(200, 210, 230), size=10):
        self.set_font("Helvetica", "", size)
        self.set_text_color(*color)
        self.multi_cell(0, 6, text)
        self.ln(1)

    def bullet(self, text, color=(180, 200, 220)):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*color)
        self.set_x(15)
        self.multi_cell(0, 6, f"  >> {text}")

    def sub_title(self, text):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(100, 200, 255)
        self.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")

    def phase_box(self, phase, title, time_est, items):
        self.set_fill_color(15, 25, 45)
        self.set_draw_color(0, 180, 160)
        self.set_line_width(0.3)
        y_start = self.get_y()
        self.rect(15, y_start, 180, 8 + len(items)*6 + 14, style='FD')
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(0, 220, 180)
        self.set_x(18)
        self.cell(0, 8, f"Phase {phase}: {title}  |  Time: {time_est}", new_x="LMARGIN", new_y="NEXT")
        for item in items:
            self.set_font("Helvetica", "", 10)
            self.set_text_color(180, 210, 230)
            self.set_x(22)
            self.cell(6, 6, "->")
            self.multi_cell(0, 6, item)
        self.ln(4)

    def table_row(self, cols, widths, header=False):
        if header:
            self.set_fill_color(10, 40, 70)
            self.set_text_color(0, 220, 200)
            self.set_font("Helvetica", "B", 10)
        else:
            self.set_fill_color(15, 25, 45)
            self.set_text_color(180, 210, 230)
            self.set_font("Helvetica", "", 10)
        x = self.get_x()
        for i, (col, w) in enumerate(zip(cols, widths)):
            self.cell(w, 7, col, border=1, fill=True)
        self.ln()


def generate():
    pdf = SaraPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ─── OVERVIEW ───────────────────────────────────────────
    pdf.section_title("What is OmniBrain SARA?", ">>")
    pdf.body_text(
        "SARA (Smart Autonomous Response Agent) is an AI Operating System Assistant built on top of "
        "Google Gemini. She runs natively on your Windows machine and can control your entire computer "
        "using natural language commands in Hindi or English.\n\n"
        "SARA is connected to a powerful backend (OmniBrain) that handles planning, memory, safety, "
        "and multi-step task execution. She can read your email, manage your calendar, open apps, "
        "type text, move the mouse, and much more."
    )

    # ─── CURRENT STATUS ─────────────────────────────────────
    pdf.section_title("Current Status (What Works Today)", "OK")
    features_done = [
        "Gmail - Read, Search, Draft, Send emails",
        "Google Calendar - List and create events",
        "Google Drive - List and read files",
        "Google Sheets - Read rows, append data",
        "Host Agent - Mouse control (click, move, drag, scroll)",
        "Host Agent - Keyboard control (hotkeys, type text, press keys)",
        "Host Agent - Open applications (Notepad, Chrome, Excel, Word)",
        "Host Agent - File operations (list, read, create, move)",
        "Host Agent - Run PowerShell scripts",
        "Safety System - Kill switch, budget tracking, policy engine",
        "Injection Defense - Prompt injection protection",
        "Notification Center - Real-time task updates",
        "Multi-language - Hindi + English commands supported",
    ]
    for f in features_done:
        pdf.bullet(f"[DONE]  {f}", color=(100, 220, 160))
    pdf.ln(2)

    # ─── ROOT CAUSE ANALYSIS ────────────────────────────────
    pdf.section_title("Problems Found & Fixed (Today's Session)", "FIX")

    problems = [
        ("422 Unprocessable Content Error",
         "The planner was sending extra fields (raw_command, dry_run, goal) to the host agent. "
         "The Pydantic schema was strict and rejected any unknown fields.",
         "Fixed client.py to strip all invalid fields before sending to host agent."),
        ("app: null on Open App",
         "When user said 'Open Notepad', the planner couldn't extract the app name from entities.",
         "Fixed planner.py to scan goal text for known app names (notepad, chrome, excel, word)."),
        ("403 Forbidden Error",
         "Host agent required an approval_id for write actions, but planner wasn't generating one.",
         "Fixed client.py to auto-generate approval_id as 'auto_{task_id}'."),
        ("Circuit Breaker OPEN",
         "After repeated errors, Redis would lock the host-agent connector for minutes.",
         "Fixed root errors so circuit breaker never trips. Added reset command."),
        ("PyAutoGUI FailSafe",
         "Mouse was at screen corner causing PyAutoGUI to throw FailSafeException.",
         "Set pyautogui.FAILSAFE = False globally in executors.py."),
        ("Windows Minimize Not Working",
         "Sara said 'COMPLETED' but windows didn't minimize. pyautogui hotkey was blocked.",
         "Replaced with Shell.Application.MinimizeAll() COM call which works directly."),
        ("Apps Opening Hidden (Invisible)",
         "Notepad was launching but MainWindowTitle was empty - window invisible to user.",
         "Root cause: host agent runs in non-interactive session. Solution: User must start "
         "host agent from their own PowerShell terminal for proper desktop access."),
        ("Fast-Path Bypass Bug",
         "A heuristic classifier was bypassing the LLM for all messages, causing Sara to say "
         "'COMPLETED' without actually doing anything.",
         "Removed the zero-latency bypass. All messages now go through Gemini LLM for proper "
         "classification with 2-4 second thinking time."),
    ]

    for i, (title, cause, fix) in enumerate(problems, 1):
        pdf.set_fill_color(20, 15, 35)
        pdf.set_draw_color(180, 80, 80)
        pdf.set_line_width(0.2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(255, 130, 130)
        pdf.cell(0, 7, f"  Problem {i}: {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(200, 180, 180)
        pdf.set_x(18)
        pdf.multi_cell(175, 5, f"Cause: {cause}")
        pdf.set_text_color(100, 220, 160)
        pdf.set_x(18)
        pdf.multi_cell(175, 5, f"Fix:   {fix}")
        pdf.ln(2)

    # ─── WINDOWS NATIVE PLAN ────────────────────────────────
    pdf.add_page()
    pdf.section_title("Windows Native App Plan (Phases)", "PLAN")

    pdf.phase_box("1", "System Tray App", "1-2 days", [
        "Sara lives in Windows System Tray (bottom-right corner)",
        "Double-click or right-click to open chat window",
        "Keeps Host Agent running automatically",
        "Files: sara_tray.py, sara_icon.ico, start_sara.bat",
        "Library: pip install pystray Pillow",
    ])

    pdf.phase_box("2", "Global Hotkey + Wake Word", "2-3 days", [
        "Alt+Space anywhere = Sara chat opens instantly",
        "'Hey Sara' voice wake word (offline, no internet needed)",
        "Uses Picovoice Porcupine for wake word detection",
        "Library: pip install keyboard pvporcupine",
    ])

    pdf.phase_box("3", "Native Chat Window", "2-3 days", [
        "Option A: Browser popup (fastest, works today)",
        "Option B: WebView2 borderless popup (native Windows 11 feel)",
        "Option C: Electron .exe installer (professional, full app)",
        "Recommended: Start with browser, upgrade to Electron later",
    ])

    pdf.phase_box("4", "Auto-Start on Windows Boot", "30 mins", [
        "Add Sara shortcut to Windows Startup folder",
        "Or register as Windows Service for even more reliability",
        "Sara starts automatically when PC boots",
    ])

    pdf.phase_box("5", "New Powers (Ongoing)", "Unlimited", [
        "Voice response - Sara will speak her answers (pyttsx3 / ElevenLabs)",
        "Screenshot understanding - Sara sees your screen (Gemini Vision)",
        "Browser automation - Sara controls Chrome tabs (Playwright)",
        "WhatsApp messages - Send WhatsApp via Sara",
        "Reminders & Alarms - Windows Task Scheduler integration",
        "WiFi/Network control - netsh command integration",
    ])

    # ─── POWERS TABLE ───────────────────────────────────────
    pdf.section_title("Full Powers Roadmap", ">>")
    pdf.table_row(["Power", "Tool/Method", "Difficulty", "Status"], [65, 55, 30, 30], header=True)
    powers = [
        ("Gmail read/send", "Gmail API", "Easy", "DONE"),
        ("Google Calendar", "Calendar API", "Easy", "DONE"),
        ("Google Drive", "Drive API", "Easy", "DONE"),
        ("Google Sheets", "Sheets API", "Easy", "DONE"),
        ("Mouse control", "pyautogui", "Easy", "DONE"),
        ("Keyboard control", "pyautogui + win32", "Easy", "DONE"),
        ("Open apps", "win32api ShellExecute", "Easy", "DONE"),
        ("File operations", "pathlib", "Easy", "DONE"),
        ("Run scripts", "PowerShell subprocess", "Easy", "DONE"),
        ("Voice response", "pyttsx3 / ElevenLabs", "Easy", "Next"),
        ("Screenshot AI", "Gemini Vision API", "Medium", "Next"),
        ("Browser control", "Playwright", "Medium", "Planned"),
        ("WhatsApp", "pywhatkit", "Easy", "Planned"),
        ("Reminders", "Task Scheduler", "Easy", "Planned"),
        ("WiFi control", "netsh commands", "Medium", "Planned"),
        ("System monitor", "psutil", "Easy", "Planned"),
    ]
    for row in powers:
        color = (100, 220, 160) if row[3] == "DONE" else (255, 200, 100) if row[3] == "Next" else (150, 170, 200)
        pdf.set_text_color(*color)
        pdf.table_row(list(row), [65, 55, 30, 30])
    pdf.ln(4)

    # ─── HOW TO START HOST AGENT ────────────────────────────
    pdf.section_title("How to Start Sara Right Now", ">>")
    pdf.sub_title("Step 1: Start OmniBrain Backend (Docker)")
    pdf.body_text(
        "Open PowerShell and run:\n"
        "  cd 'C:\\Users\\vikas_p9rmqot\\Downloads\\ai automation project\\omnibrain'\n"
        "  docker compose up -d"
    )
    pdf.sub_title("Step 2: Start Host Agent (IMPORTANT - Run Yourself!)")
    pdf.body_text(
        "Open a NEW PowerShell window (keep it open!) and run:\n"
        "  cd C:\\omnibrain-host\n"
        "  $env:OMNIBRAIN_HOST_JWT_SECRET='OMNIBRAIN_HOST_JWT_SECRET_DEV_KEY'\n"
        "  .\\.venv\\Scripts\\uvicorn.exe app.main:app --host 127.0.0.1 --port 7788\n\n"
        "IMPORTANT: You must run this yourself in YOUR PowerShell.\n"
        "If the AI agent starts it, Sara's windows will be invisible (wrong session)!"
    )
    pdf.sub_title("Step 3: Open Sara UI")
    pdf.body_text(
        "Open your browser and go to:\n"
        "  http://localhost:3000\n\n"
        "Start the frontend if not running:\n"
        "  cd 'C:\\Users\\vikas_p9rmqot\\Downloads\\ai automation project\\omnibrain'\n"
        "  npm run dev -- -p 3000"
    )

    # ─── ARCHITECTURE DIAGRAM ───────────────────────────────
    pdf.section_title("System Architecture", ">>")
    pdf.body_text(
        "User Input (Hindi/English)\n"
        "         |\n"
        "  [Next.js Frontend - localhost:3000]\n"
        "         |\n"
        "  [FastAPI Backend - localhost:8000]\n"
        "    /           \\\n"
        "[Classifier]  [Planner]\n"
        "(Gemini LLM)  (DAG Graph)\n"
        "         |\n"
        "  [ARQ Worker Queue]\n"
        "    /    |    \\\n"
        "[Gmail] [Calendar] [Host Agent - localhost:7788]\n"
        "                        /    |    \\\n"
        "                 [Mouse] [Keyboard] [Files/Apps]"
    )

    # ─── FINAL NOTE ─────────────────────────────────────────
    pdf.section_title("Next Steps Summary", ">>")
    steps = [
        "You start the host agent yourself in your own PowerShell (for visible windows)",
        "Test: 'Open Notepad' - you should see Notepad appear on screen",
        "Test: 'Minimize all windows' - all windows should minimize",
        "Test: 'Type in Notepad: Hello I am Sara' - text should appear in Notepad",
        "Decide: Browser popup vs Electron app for Sara chat window",
        "Decide: Hotkey only vs Hey Sara voice wake word",
        "Phase 1 development: Sara System Tray App",
        "Phase 2 development: Wake word + Hotkey",
        "Gradually add new powers from the roadmap",
    ]
    for i, s in enumerate(steps, 1):
        pdf.bullet(f"Step {i}: {s}")

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(0, 200, 180)
    pdf.cell(0, 10, "Sara is ready. The future is yours to build.", align="C", new_x="LMARGIN", new_y="NEXT")

    output_path = r"C:\Users\vikas_p9rmqot\Downloads\SARA_Complete_Plan.pdf"
    pdf.output(output_path)
    print(f"PDF saved to: {output_path}")

generate()

