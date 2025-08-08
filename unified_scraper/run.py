from database.insert_csv import insert_judgment_from_csv

if __name__ == "__main__":
    csv_path = "delhi_result.csv"  # Path relative to project root
    insert_judgment_from_csv(csv_path)
