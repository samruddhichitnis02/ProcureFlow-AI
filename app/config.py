import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseModel):
    APP_NAME: str = "ProcureFlow AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{DATA_DIR / 'procureflow.db'}"
    )

    # Vector store
    FAISS_INDEX_PATH: str = os.getenv(
        "FAISS_INDEX_PATH", str(DATA_DIR / "faiss_index.bin")
    )
    FAISS_METADATA_PATH: str = os.getenv(
        "FAISS_METADATA_PATH", str(DATA_DIR / "faiss_metadata.json")
    )
    EMBEDDING_MODEL_NAME: str = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Agent / LLM
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # "mock", "claude", "ollama"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")

    # Guardrails & Risk Thresholds
    HIGH_RISK_REFUND_THRESHOLD: float = float(
        os.getenv("HIGH_RISK_REFUND_THRESHOLD", "100.0")
    )
    TARGET_P95_LATENCY_MS: float = 800.0


settings = Settings()

