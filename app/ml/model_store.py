from pathlib import Path
from typing import Any, Optional
import joblib
import pickle
import logging

log = logging.getLogger("ml.model_store")

def save_model(model: Any, path: str) -> None:
    """Всегда сохраняем через joblib."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, str(p))

def load_model_joblib(path: str) -> Any:
    return joblib.load(path)

def load_model_pickle(path: str) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)

def load_model_any(path: str) -> Any:
    """Пробуем joblib, затем pickle — помогает пережить «несовпадение форматов»."""
    try:
        m = load_model_joblib(path)
        log.debug("Loaded model via joblib: %s", path)
        return m
    except Exception as e1:
        log.debug("Joblib load failed (%s), trying pickle: %s", type(e1).__name__, path)
        try:
            m = load_model_pickle(path)
            log.debug("Loaded model via pickle: %s", path)
            return m
        except Exception as e2:
            log.error("Both joblib & pickle load failed for %s: %s / %s", path, e1, e2)
            raise
