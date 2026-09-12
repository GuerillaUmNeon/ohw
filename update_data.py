from pathlib import Path
import shutil
import kagglehub

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

kagglehub.dataset_download("ludmin/billboard", output_dir=str(DATA_DIR))

for item in DATA_DIR.iterdir():
    if item.name != "hot100.csv":
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

print("Dataset updated. Only data/hot100.csv was kept.")