from fpdf import FPDF
import datetime

class PDF(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(40, 60, 100)
        self.cell(0, 10, 'OmniBrain (S.A.R.A.) - Comprehensive Technical Documentation', align='C')
        self.ln(12)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()} | Generated on: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', align='C')

    def chapter_title(self, num, title):
        self.set_font('helvetica', 'B', 14)
        self.set_fill_color(220, 230, 245)
        self.set_text_color(10, 30, 80)
        self.cell(0, 10, f'Section {num}: {title}', fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

    def chapter_body(self, body):
        self.set_x(15)
        self.set_font('helvetica', '', 10)
        self.set_text_color(0, 0, 0)
        self.multi_cell(0, 6, body)
        self.ln(6)
        
    def add_bullet(self, text):
        self.set_x(15)
        self.set_font('helvetica', '', 10)
        self.multi_cell(0, 6, f"  - {text}")

pdf = PDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# --- SECTION 1 ---
pdf.chapter_title("1", "Executive Summary & Core Architecture")
body1 = (
    "OmniBrain is a highly advanced, autonomous AI Operating System built for extreme speed and precision. "
    "At its core is S.A.R.A. (Smart Autonomous Responsive Assistant). The system is containerized using Docker, "
    "orchestrating multiple microservices:\n\n"
    "- Frontend: Next.js 15, React 19, Tailwind CSS, providing a real-time Chat UI.\n"
    "- Backend: FastAPI (Python 3.12) utilizing asynchronous endpoints for zero-blocking operations.\n"
    "- Database: PostgreSQL 16 equipped with 'pgvector' for high-dimensional memory embeddings.\n"
    "- Message Broker & Cache: Redis 7 for instant response caching and background task queueing (Arq).\n"
    "- AI Model: Integrated with Gemini (gemini-3.5-flash-lite / 3.8-pro) via a dynamic ModelRouter."
)
pdf.chapter_body(body1)

# --- SECTION 2 ---
pdf.chapter_title("2", "The Cognitive Brain Engine (A.I. Pipeline)")
pdf.chapter_body("The 'Brain' of Sara operates through an ultra-fast, multi-stage pipeline to process user intent:")
pdf.add_bullet("IntentEngine: Uses a sub-millisecond heuristic fast-path. It analyzes the raw user query and classifies it as either 'Conversational' (greeting/QA) or 'Actionable' (requires tool execution).")
pdf.add_bullet("ContextEngine: Rapidly queries PostgreSQL to assemble the User Profile, active connected integrations, recent background tasks, and long-term vector memories into a dynamic context snippet.")
pdf.add_bullet("DAGPlanner (Directed Acyclic Graph): If a task is actionable, the Planner breaks it down into a logical sequence of steps. For example, 'Find latest email and summarize' becomes [Step 1: gmail.read] -> [Step 2: internal.summarize].")
pdf.add_bullet("ResultSynthesizer: Once the background worker completes the DAG steps, the Synthesizer compiles the raw JSON outputs into a natural, spoken-language report for Sara to speak.")
pdf.ln(5)

# --- SECTION 3 ---
pdf.chapter_title("3", "Integrations, Tools, and Connectors")
pdf.chapter_body("Sara is equipped with real-world tool connectors allowing her to read, write, and execute external actions:")
pdf.add_bullet("Google Mail (Gmail): Full read/write access. Sara can search mailboxes, draft new emails, and send emails directly using OAuth2 tokens.")
pdf.add_bullet("Google Calendar: Capability to read upcoming events and schedule new meetings seamlessly.")
pdf.add_bullet("Google Drive: Search capabilities across the entire Drive workspace.")
pdf.add_bullet("Google Sheets: Read rows, update specific cells, and append new rows to spreadsheets.")
pdf.add_bullet("Web Search Agent: Integrated with DuckDuckGo Search API to fetch live, real-time internet data. If a user asks for 'latest news', Sara scrapes the web dynamically.")
pdf.ln(5)

# --- SECTION 4 ---
pdf.chapter_title("4", "Voice Mode & Human-Like Personality")
body4 = (
    "Sara's interaction layer has been completely overhauled to mimic 'ChatGPT Voice Mode' behavior.\n\n"
    "1. Text-to-Speech (TTS): Utilizing Microsoft Edge Neural TTS (edge-tts). The default Hindi/Hinglish voice is 'hi-IN-SwaraNeural'. "
    "We applied custom acoustic tuning (Pitch: -2Hz, Rate: +5%) to remove robotic artifacts, making her sound relaxed and deeply human.\n\n"
    "2. System Prompt Engineering: Sara operates under strict personality constraints. She is instructed to act warm, empathetic, and professional. "
    "She uses natural conversational Indian fillers (e.g., 'Haan ji', 'Dekhiye', 'Bataiye') instead of robotic, bullet-point lists."
)
pdf.chapter_body(body4)

# --- SECTION 5 ---
pdf.chapter_title("5", "Extreme Performance Optimizations")
body5 = (
    "To achieve 'Flash Speed' (responses under 1 second), several critical low-level optimizations were implemented:\n\n"
    "- Pre-Warmed Singletons: Previously, engines (Router, Context, Planner) were initialized on every request, costing ~500ms. "
    "They are now instantiated once at startup and shared across the application.\n"
    "- Redis Response Caching: Common conversational queries are hashed and cached in Redis with a 5-minute TTL. Repeated questions return in literally 0ms.\n"
    "- SSE Streaming (Server-Sent Events): Replaced synchronous waiting with an async generator. Sara's response streams word-by-word to the Next.js UI, giving the illusion of instant generation."
)
pdf.chapter_body(body5)

# --- SECTION 6 ---
pdf.chapter_title("6", "Security & Concurrency")
body6 = (
    "- Authentication: Implemented secure JWT (JSON Web Tokens) with a 30-minute expiry for API security.\n"
    "- Safe Task Execution: Destructive tasks (e.g., deleting files, sending emails) are routed to a 'WAITING_APPROVAL' state, ensuring human-in-the-loop validation.\n"
    "- Arq Redis Workers: Tool execution happens entirely in the background. The main API thread is never blocked, allowing OmniBrain to handle hundreds of concurrent requests."
)
pdf.chapter_body(body6)

# --- SECTION 7 ---
pdf.chapter_title("7", "Upcoming / Work-in-Progress")
pdf.chapter_body(
    "OmniBrain is continuously evolving. The next immediate milestone is the Windows Host Agent (Local PC Control). "
    "Because OmniBrain runs safely inside a Docker Linux Sandbox, it cannot directly control the host Windows PC. "
    "We are designing a bridge script (`host_agent.py`) that will allow Sara to break out of the sandbox to open local files, "
    "type on the keyboard, and execute native Windows CMD operations."
)

pdf.output('OmniBrain_SARA_Complete_DeepDive.pdf')
print("Deep dive PDF generated.")
