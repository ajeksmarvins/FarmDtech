"""Model training entrypoint: python price_predictor.py"""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parent / "scripts/train_models.py"), run_name="__main__")
