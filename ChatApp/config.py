import os
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
SANDBOX_SERVICE_URL = os.getenv("SANDBOX_SERVICE_URL", "http://127.0.0.1:8020")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

DATABASE_URL = "chat.db"
UPLOAD_DIR = "uploads"

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")

system_prompt_with_code_exec_default = (
    "You can execute shell commands and python codes in a isolated sandbox(docker-python3.12-workspace). The network is disabled for security.\n"
    "Available pip packages: numpy, pandas, scipy, sympy, openpyxl, python-docx, PyPDF2, lxml, beautifulsoup4, matplotlib, seaborn, pylint.\n"
    "Installed fonts: wqy-microhei"
    "You should utilize your code execution ability to improve your response and user experience.\n"
    "You can operate files in the sandbox freely through shell or python code.\n"
    "Files send by user will be in /workspace/.You can also export files to user.\n"
    "Every operation in the sandbox is logged in /workplace/exec_log.txt."
)
SYSTEM_PROMPT_WITH_CODE_EXEC = os.getenv("SYSTEM_PROMPT_WITH_CODE_EXEC", system_prompt_with_code_exec_default)
system_prompt_default = "You are a helpful assistant."
SYSTEM_PROMPT_DEFAULT = os.getenv("SYSTEM_PROMPT_DEFAULT", system_prompt_default)

# 必须设置的项
assert JWT_SECRET_KEY
assert ADMIN_API_KEY