"""
download.py — fetch UCI Amazon Access Samples (id=216) and save to data/raw/.

Strategy:
  1. Try ucimlrepo API (fast, structured).
  2. Fall back to direct HTTP download of the UCI zip archive.
  Dataset page: https://archive.ics.uci.edu/dataset/216/amazon+access+samples
"""
import io
import zipfile
import urllib.request
from pathlib import Path
from loguru import logger
from role_recommender.config import DATA_RAW, UCI_DATASET_ID, RAW_DATASET

UCI_ZIP_URL = (
    "https://archive.ics.uci.edu/static/public/216/amazon+access+samples.zip"
)


def _try_ucimlrepo() -> bool:
    """Attempt download via ucimlrepo API. Returns True on success."""
    try:
        from ucimlrepo import fetch_ucirepo
        logger.info(f"Trying ucimlrepo API for dataset {UCI_DATASET_ID} …")
        dataset = fetch_ucirepo(id=UCI_DATASET_ID)
        df = dataset.data.original
        df.to_csv(RAW_DATASET, index=False)
        logger.success(f"Saved {len(df):,} rows via ucimlrepo → {RAW_DATASET}")
        return True
    except Exception as e:
        logger.warning(f"ucimlrepo failed ({e}) — falling back to direct download.")
        return False


def _try_direct_download() -> bool:
    """Stream UCI zip to disk, extract tgz to disk, read the CSV. No large in-memory buffers."""
    import tarfile
    import tempfile
    import shutil
    import pandas as pd

    tmp_dir = Path(tempfile.mkdtemp(prefix="role_recommender_"))
    try:
        zip_path = tmp_dir / "dataset.zip"
        tgz_path = tmp_dir / "dataset.tgz"

        # Step 1: stream zip to disk
        logger.info(f"Streaming zip to {zip_path} …")
        urllib.request.urlretrieve(UCI_ZIP_URL, zip_path)
        logger.info(f"Zip downloaded ({zip_path.stat().st_size / 1e6:.1f} MB)")

        # Step 2: extract tgz from zip to disk
        with zipfile.ZipFile(zip_path) as zf:
            members = zf.namelist()
            logger.info(f"Zip contents: {members}")
            tgz_names = [n for n in members if n.endswith(".tgz") or n.endswith(".tar.gz")]
            csv_names = [n for n in members if n.lower().endswith(".csv")]

            if csv_names:
                zf.extract(csv_names[0], tmp_dir)
                csv_path = tmp_dir / csv_names[0]
            elif tgz_names:
                logger.info(f"Extracting {tgz_names[0]} from zip …")
                zf.extract(tgz_names[0], tmp_dir)
                tgz_path = tmp_dir / tgz_names[0]

                # Step 3: extract CSV from tgz to disk
                with tarfile.open(tgz_path, mode="r:gz") as tar:
                    tar_members = tar.getnames()
                    logger.info(f"Tar contents: {tar_members}")
                    csv_in_tar = [m for m in tar_members if m.lower().endswith(".csv")]
                    if not csv_in_tar:
                        logger.error(f"No CSV in tar. Contents: {tar_members}")
                        return False
                    # Extract only the first (main) CSV
                    tar.extract(csv_in_tar[0], tmp_dir)
                    csv_path = tmp_dir / csv_in_tar[0]
            else:
                logger.error(f"No CSV or tgz in zip. Contents: {members}")
                return False

        # Step 4: read from disk and save to data/raw/
        logger.info(f"Reading CSV from {csv_path} …")
        df = pd.read_csv(csv_path)
        df.to_csv(RAW_DATASET, index=False)
        logger.success(f"Saved {len(df):,} rows → {RAW_DATASET}")
        return True

    except Exception as e:
        logger.error(f"Direct download failed: {e}")
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def download() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)

    if RAW_DATASET.exists():
        logger.info(f"Dataset already exists at {RAW_DATASET} — skipping download.")
        return

    if _try_ucimlrepo():
        return

    if _try_direct_download():
        return

    raise RuntimeError(
        "Could not download the dataset automatically.\n"
        "Manual fallback: download from Kaggle (Amazon Employee Access Challenge)\n"
        "  https://www.kaggle.com/c/amazon-employee-access-challenge/data\n"
        f"and save the train.csv as: {RAW_DATASET}"
    )


if __name__ == "__main__":
    download()
