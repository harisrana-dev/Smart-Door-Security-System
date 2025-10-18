import csv
import os
from datetime import datetime

def log_entry(name, similarity, verified, log_path="logs/recognition_log.csv"):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([
            now,
            name,
            f"{similarity:.2f}" if similarity is not None else "",
            "Verified" if verified else "Not Verified"
        ])
