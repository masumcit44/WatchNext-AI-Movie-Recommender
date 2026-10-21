#!/usr/bin/env python3
"""
Build poster_paths.json from movies_metadata.csv (Kaggle TMDB 5000 dataset).

Reads the "id" and "poster_path" columns, matches against our movies.json,
and writes a mapping {"<movie_id>": "/path.jpg"} to model/artifacts/poster_paths.json.
No API key required - purely local processing.
"""
import argparse
import csv
import json
import sys
from pathlib import Path


def find_repo_root(script_path: Path) -> Path:
    """Find repo root by looking for model/artifacts/movies.json."""
    current = script_path.resolve()
    for parent in [current] + list(current.parents):
        if (parent / "model" / "artifacts" / "movies.json").exists():
            return parent
    return current.parents[2]  # fallback: scripts/ -> repo/


def load_movie_ids(artifacts_dir: Path) -> set[int]:
    """Load all movie_ids from movies.json."""
    movies_path = artifacts_dir / "movies.json"
    if not movies_path.exists():
        raise FileNotFoundError(f"movies.json not found at {movies_path}")
    with open(movies_path, encoding="utf-8") as f:
        movies = json.load(f)
    return {int(m["movie_id"]) for m in movies}


def is_valid_poster_path(poster_path: str) -> bool:
    """Check if poster_path is a valid TMDB path."""
    if not poster_path or not isinstance(poster_path, str):
        return False
    p = poster_path.strip()
    return p.startswith("/") and p.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))


def build_poster_mapping(
    csv_path: Path,
    artifacts_dir: Path,
    output_path: Path,
) -> dict:
    """Build the poster mapping from CSV."""
    known_ids = load_movie_ids(artifacts_dir)
    print(f"Loaded {len(known_ids)} movie IDs from movies.json")

    poster_map: dict[int, str] = {}
    seen_ids: set[int] = set()
    malformed_rows = 0
    duplicate_ids = 0
    empty_poster = 0
    invalid_poster = 0
    unknown_ids = 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = row.get("id", "").strip()
            poster = row.get("poster_path", "").strip()

            # Skip malformed id (not a pure integer)
            try:
                movie_id = int(raw_id)
            except (ValueError, TypeError):
                malformed_rows += 1
                continue

            # Skip duplicates - keep first non-empty poster_path
            if movie_id in seen_ids:
                duplicate_ids += 1
                if movie_id in poster_map and poster_map[movie_id] and not poster:
                    # We already have a poster for this id, skip empty
                    continue
                if not poster:
                    # New entry has no poster, keep existing
                    continue
                # New entry has a poster, update (but we prefer first non-empty)
                if movie_id not in poster_map or not poster_map[movie_id]:
                    poster_map[movie_id] = poster
                continue

            seen_ids.add(movie_id)

            # Check if this movie is in our dataset
            if movie_id not in known_ids:
                unknown_ids += 1
                continue

            # Validate poster path
            if not poster:
                empty_poster += 1
                continue
            if not is_valid_poster_path(poster):
                invalid_poster += 1
                continue

            poster_map[movie_id] = poster.strip()

    # Sort by id and convert to string keys for JSON
    sorted_map = {str(k): poster_map[k] for k in sorted(poster_map.keys())}

    # Write atomically
    temp_path = output_path.with_suffix(".json.tmp")
    with open(temp_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sorted_map, f, ensure_ascii=False, separators=(",", ":"))
    temp_path.replace(output_path)

    # Stats
    total_known = len(known_ids)
    with_poster = len(sorted_map)
    missing = total_known - with_poster
    coverage = (with_poster / total_known * 100) if total_known > 0 else 0

    print(f"\nResults:")
    print(f"  Total movies in dataset: {total_known}")
    print(f"  Movies with poster:      {with_poster}")
    print(f"  Movies without poster:   {missing}")
    print(f"  Coverage:                {coverage:.1f}%")
    print(f"  CSV malformed rows:      {malformed_rows}")
    print(f"  CSV duplicate ids:       {duplicate_ids}")
    print(f"  Empty poster paths:      {empty_poster}")
    print(f"  Invalid poster paths:    {invalid_poster}")
    print(f"  Unknown movie ids:       {unknown_ids}")
    print(f"  Output written to:       {output_path}")

    # Sample of movies without posters
    missing_ids = known_ids - set(poster_map.keys())
    if missing_ids:
        # Load titles for missing ids
        movies_path = artifacts_dir / "movies.json"
        with open(movies_path, encoding="utf-8") as f:
            movies = json.load(f)
        id_to_title = {int(m["movie_id"]): m["title"] for m in movies}
        sample_missing = sorted(missing_ids)[:15]
        print(f"\nSample of {len(sample_missing)} movies without posters:")
        for mid in sample_missing:
            print(f"  {mid}: {id_to_title.get(mid, 'Unknown')}")

    return sorted_map


def validate_output(output_path: Path, artifacts_dir: Path) -> bool:
    """Validate the generated poster_paths.json."""
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)

    known_ids = load_movie_ids(artifacts_dir)

    for k, v in data.items():
        # Key must be a known movie id
        try:
            mid = int(k)
        except ValueError:
            print(f"ERROR: Key '{k}' is not a valid integer")
            return False
        if mid not in known_ids:
            print(f"ERROR: Movie id {mid} not in movies.json")
            return False
        # Value must start with "/" and end with valid extension
        if not isinstance(v, str) or not v.startswith("/"):
            print(f"ERROR: Value '{v}' for id {k} does not start with '/'")
            return False
        if not v.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            print(f"ERROR: Value '{v}' for id {k} has invalid extension")
            return False

    print("Validation passed: all keys are known movie ids, all values are valid poster paths")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Build poster_paths.json from movies_metadata.csv"
    )
    parser.add_argument(
        "--csv",
        default="data/movies_metadata.csv",
        help="Path to movies_metadata.csv (default: data/movies_metadata.csv relative to repo root)",
    )
    parser.add_argument(
        "--artifacts",
        default="model/artifacts",
        help="Path to artifacts directory (default: model/artifacts)",
    )
    parser.add_argument(
        "--output",
        help="Output path for poster_paths.json (default: <artifacts>/poster_paths.json)",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = find_repo_root(script_path)

    csv_path = (repo_root / args.csv).resolve()
    artifacts_dir = (repo_root / args.artifacts).resolve()

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = artifacts_dir / "poster_paths.json"

    print(f"Repo root:        {repo_root}")
    print(f"CSV path:         {csv_path}")
    print(f"Artifacts dir:    {artifacts_dir}")
    print(f"Output path:      {output_path}")

    if not csv_path.exists():
        print(f"\nERROR: CSV file not found at {csv_path}")
        print("Please download movies_metadata.csv from Kaggle (TMDB 5000 Movie Dataset)")
        print("and place it at data/movies_metadata.csv relative to the repo root.")
        print("Download: https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata")
        sys.exit(2)

    try:
        mapping = build_poster_mapping(csv_path, artifacts_dir, output_path)
        if not validate_output(output_path, artifacts_dir):
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()