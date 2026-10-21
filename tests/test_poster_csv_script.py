#!/usr/bin/env python3
"""
Tests for scripts/build_poster_paths_from_csv.py
"""
import csv
import json
import tempfile
import subprocess
import sys
from pathlib import Path


def test_build_script_help():
    """Test script runs and shows help."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "movies_metadata.csv" in result.stdout


def test_build_script_missing_csv():
    """Test script exits with code 2 and clear message when CSV is missing."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        fake_csv = tmpdir / "nonexistent.csv"
        fake_artifacts = tmpdir / "artifacts"
        fake_artifacts.mkdir()
        # Create minimal movies.json
        movies = [{"movie_id": 1, "title": "Test"}]
        (fake_artifacts / "movies.json").write_text(json.dumps(movies))

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(fake_csv),
            "--artifacts", str(fake_artifacts),
        ], capture_output=True, text=True)
        assert result.returncode == 2
        assert "CSV file not found" in result.stdout or "CSV file not found" in result.stderr
        assert "Kaggle" in result.stdout or "Kaggle" in result.stderr


def test_build_script_malformed_ids():
    """Test script skips rows with malformed IDs."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        # Create movies.json with known IDs
        movies = [
            {"movie_id": 1, "title": "Movie 1"},
            {"movie_id": 2, "title": "Movie 2"},
            {"movie_id": 3, "title": "Movie 3"},
        ]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        # Create CSV with malformed rows
        rows = [
            ["id", "poster_path"],
            ["1", "/valid1.jpg"],           # valid
            ["not-an-int", "/valid2.jpg"],  # malformed id
            ["2.5", "/valid3.jpg"],         # malformed id (float)
            ["", "/valid4.jpg"],            # empty id
            ["3", "/valid5.jpg"],           # valid
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        # Only IDs 1 and 3 should be present (valid integers)
        assert set(output.keys()) == {"1", "3"}
        assert output["1"] == "/valid1.jpg"
        assert output["3"] == "/valid5.jpg"


def test_build_script_duplicate_ids():
    """Test script keeps first non-empty poster_path for duplicate IDs."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [{"movie_id": 1, "title": "Movie 1"}]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        # First entry has no poster, second has poster - should keep second
        # First entry has poster, second empty - should keep first
        rows = [
            ["id", "poster_path"],
            ["1", ""],              # first entry, empty poster
            ["1", "/first_poster.jpg"],  # duplicate, has poster - should use this
            ["1", "/second_poster.jpg"], # another duplicate, should be ignored
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        assert output["1"] == "/first_poster.jpg"


def test_build_script_empty_and_invalid_posters():
    """Test script skips empty and invalid poster paths."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [
            {"movie_id": 1, "title": "Movie 1"},
            {"movie_id": 2, "title": "Movie 2"},
            {"movie_id": 3, "title": "Movie 3"},
            {"movie_id": 4, "title": "Movie 4"},
            {"movie_id": 5, "title": "Movie 5"},
        ]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        rows = [
            ["id", "poster_path"],
            ["1", "/valid.jpg"],      # valid
            ["2", ""],                # empty
            ["3", "   "],             # whitespace
            ["4", "no-slash.jpg"],    # no leading slash
            ["5", "/valid.png"],      # valid .png
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        assert set(output.keys()) == {"1", "5"}
        assert output["1"] == "/valid.jpg"
        assert output["5"] == "/valid.png"


def test_build_script_unknown_ids():
    """Test script skips IDs not in movies.json."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [{"movie_id": 1, "title": "Movie 1"}]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        rows = [
            ["id", "poster_path"],
            ["1", "/valid.jpg"],      # known
            ["999", "/unknown.jpg"],  # unknown
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        assert set(output.keys()) == {"1"}


def test_build_script_runs_from_different_cwd():
    """Test script works when run from a different working directory."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [{"movie_id": 1, "title": "Movie 1"}]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        rows = [
            ["id", "poster_path"],
            ["1", "/valid.jpg"],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        # Run from a different directory
        other_dir = tmpdir / "other"
        other_dir.mkdir()

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True, cwd=str(other_dir))

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        assert output["1"] == "/valid.jpg"


def test_build_script_output_sorted():
    """Test output keys are sorted by integer ID."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [
            {"movie_id": 10, "title": "Movie 10"},
            {"movie_id": 2, "title": "Movie 2"},
            {"movie_id": 100, "title": "Movie 100"},
        ]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        rows = [
            ["id", "poster_path"],
            ["10", "/a.jpg"],
            ["2", "/b.jpg"],
            ["100", "/c.jpg"],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        output = json.loads(output_path.read_text())
        # Keys should be sorted by integer value
        keys = list(output.keys())
        assert keys == ["2", "10", "100"]


def test_build_script_output_valid_json():
    """Test output is valid JSON with LF endings."""
    script = Path(__file__).parent.parent / "scripts" / "build_poster_paths_from_csv.py"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "test.csv"
        artifacts_dir = tmpdir / "artifacts"
        artifacts_dir.mkdir()
        output_path = artifacts_dir / "poster_paths.json"

        movies = [{"movie_id": 1, "title": "Movie 1"}]
        (artifacts_dir / "movies.json").write_text(json.dumps(movies))

        rows = [
            ["id", "poster_path"],
            ["1", "/test.jpg"],
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        result = subprocess.run([
            sys.executable, str(script),
            "--csv", str(csv_path),
            "--artifacts", str(artifacts_dir),
            "--output", str(output_path),
        ], capture_output=True, text=True)

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        # Read raw bytes to check line endings
        content = output_path.read_bytes()
        assert b"\r\n" not in content, "Output contains CRLF line endings"
        assert content.endswith(b"}") or content.endswith(b"}\n"), "Invalid JSON ending"
        # Validate it parses
        parsed = json.loads(content)
        assert parsed["1"] == "/test.jpg"