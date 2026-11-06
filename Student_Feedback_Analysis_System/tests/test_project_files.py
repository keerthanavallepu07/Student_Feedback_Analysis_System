from pathlib import Path

def test_required_project_files_exist():
    root=Path(__file__).resolve().parents[1]
    for name in ["app.py","schema.sql","requirements.txt",".env.example","README.md"]:
        assert (root/name).exists()
