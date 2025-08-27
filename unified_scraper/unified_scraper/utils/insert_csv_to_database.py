import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from Database.models import MetaData, HighCourt
from Database.high_court_database import SessionLocal
import os
import json



def insert_judgments_from_csv(csv_path: str, high_court_name: str, base_link: str, bench_name: str, pdf_folder: str):
    """
    Insert judgment metadata from CSV into DB, avoiding duplicates based on
    (case_id, document_link, high_court_id) combination.
    Each (case_id, pdf_link) becomes a new row instead of appending to JSON.
    """
    #  Load CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f" Failed to read CSV: {e}")
        return

    required_columns = ['case_no', 'date', 'party', 'pdf_link']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        print(f"Missing columns in CSV: {missing}")
        return

    df = df[required_columns]
    print(f" Loaded {len(df)} rows from '{csv_path}'")

    session: Session = SessionLocal()

    try:
        # Ensure High Court exists
        highcourt = (
            session.query(HighCourt)
            .filter(
                HighCourt.highcourt_name == high_court_name,
                HighCourt.bench == bench_name
            )
            .first()
        )
        if not highcourt:
            highcourt = HighCourt(
                highcourt_name=high_court_name,
                base_link=base_link,
                bench=bench_name,
                pdf_folder=pdf_folder
            )
            session.add(highcourt)
            session.commit()
            session.refresh(highcourt)
            print(f"Added new High Court: {high_court_name}")

        # Load existing (case_id, document_link) pairs
        rows = (
            session.query(MetaData.case_id, MetaData.document_link)
            .filter_by(high_court_id=highcourt.id)
            .all()
        )
        existing_pairs: set[tuple[str, str]] = set()
        for row in rows:
            links = []
            if row.document_link:
                if isinstance(row.document_link, str):
                    try:
                        links = json.loads(row.document_link)
                    except Exception:
                        links = [row.document_link]
                elif isinstance(row.document_link, list):
                    links = row.document_link
            for link in links:
                existing_pairs.add((row.case_id, link))

        insert_count = 0
        skip_count = 0
        seen_csv_pairs = set()  

        for idx, row in df.iterrows():
            case_id = str(row['case_no']).strip() if pd.notna(row['case_no']) else None
            raw_date = str(row['date']).strip() if pd.notna(row['date']) else None
            party_detail = str(row['party']).strip() if pd.notna(row['party']) else None
            document_link = str(row['pdf_link']).strip() if pd.notna(row['pdf_link']) else None

            if not all([case_id, raw_date, party_detail, document_link]):
                print(f"Row {idx} skipped: Missing fields.")
                skip_count += 1
                continue

            # Normalize pair
            pair = (case_id, document_link)

            if pair in existing_pairs:
                print(f"Row {idx} skipped: Already in DB (case_id={case_id}, link={document_link})")
                skip_count += 1
                continue

            if pair in seen_csv_pairs:
                print(f"Row {idx} skipped: Duplicate inside CSV (case_id={case_id}, link={document_link})")
                skip_count += 1
                continue

            # Insert new row
            metadata = MetaData(
                high_court_id=highcourt.id,
                case_id=case_id,
                judgement_date=raw_date,
                party_detail=party_detail,
                document_link=json.dumps([document_link]),
                scrapped_at=datetime.now(),
                is_downloaded=False
            )
            session.add(metadata)
            insert_count += 1
            seen_csv_pairs.add(pair)

        try:
            session.commit()
            print(f"\n Migration completed.")
            print(f" Records inserted: {insert_count}")
            print(f" Records skipped : {skip_count}")

            if os.path.exists(csv_path):
                os.remove(csv_path)
                print(f"Deleted CSV file: {csv_path}")
            
            if os.path.exists('results.xlsx'):
                os.remove('results.xlsx')
                print(f"excel file also removed")

        except IntegrityError as e:
            session.rollback()
            print(f"Commit failed due to IntegrityError: {e}")

    except Exception as e:
        session.rollback()
        print(f" Unexpected error: {e}")
    finally:
        session.close()



def insert_judgments_from_csv_with_benches(csv_path: str, high_court_name: str, base_link: str, bench_name: str, pdf_folder: str):
    """
    Insert judgment metadata from CSV into DB, but only for the given bench.
    Each (case_id, pdf_link) becomes a new row instead of appending to JSON.
    """

    # Load CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        return

    required_columns = ['bench', 'case_no', 'date', 'party', 'pdf_link']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        print(f"Missing columns in CSV: {missing}")
        return

    # Keep only the rows for the given bench_name
    df = df[df['bench'].str.strip().str.lower() == bench_name.strip().lower()]
    if df.empty:
        print(f"No rows found for bench '{bench_name}' in '{csv_path}'")
        return

    df = df[required_columns]
    print(f"Loaded {len(df)} rows for bench '{bench_name}' from '{csv_path}'")

    session: Session = SessionLocal()

    try:
        # Ensure High Court with given bench exists
        highcourt = (
            session.query(HighCourt)
            .filter(
                HighCourt.highcourt_name == high_court_name,
                HighCourt.bench == bench_name
            )
            .first()
        )
        if not highcourt:
            highcourt = HighCourt(
                highcourt_name=high_court_name,
                base_link=base_link,
                bench=bench_name,
                pdf_folder=pdf_folder
            )
            session.add(highcourt)
            session.commit()
            session.refresh(highcourt)
            print(f"Added new High Court Bench: {high_court_name} ({bench_name})")

        # Load existing (case_id, document_link) pairs for this bench
        rows = (
            session.query(MetaData.case_id, MetaData.document_link)
            .filter_by(high_court_id=highcourt.id)
            .all()
        )
        existing_pairs: set[tuple[str, str]] = set()
        for row in rows:
            links = []
            if row.document_link:
                if isinstance(row.document_link, str):
                    try:
                        links = json.loads(row.document_link)
                    except Exception:
                        links = [row.document_link]
                elif isinstance(row.document_link, list):
                    links = row.document_link
            for link in links:
                existing_pairs.add((row.case_id, link))

        insert_count = 0
        skip_count = 0
        seen_csv_pairs = set()

        for idx, row in df.iterrows():
            case_id = str(row['case_no']).strip() if pd.notna(row['case_no']) else None
            raw_date = str(row['date']).strip() if pd.notna(row['date']) else None
            party_detail = str(row['party']).strip() if pd.notna(row['party']) else None
            document_link = str(row['pdf_link']).strip() if pd.notna(row['pdf_link']) else None


            if not all([case_id, raw_date, document_link]):
                print(f"Row {idx} skipped: Missing fields.")
                skip_count += 1
                continue

            # Normalize pair
            pair = (case_id, document_link)

            if pair in existing_pairs:
                print(f"Row {idx} skipped: Already in DB (case_id={case_id}, link={document_link})")
                skip_count += 1
                continue

            if pair in seen_csv_pairs:
                print(f"Row {idx} skipped: Duplicate inside CSV (case_id={case_id}, link={document_link})")
                skip_count += 1
                continue

            # Insert new row
            metadata = MetaData(
                high_court_id=highcourt.id,
                case_id=case_id,
                judgement_date=raw_date,
                party_detail=party_detail,
                document_link=json.dumps([document_link]),
                scrapped_at=datetime.now(),
                is_downloaded=False
            )
            
            session.add(metadata)
            insert_count += 1
            seen_csv_pairs.add(pair)

        try:
            session.commit()
            print(f"\nMigration completed for bench '{bench_name}'.")
            print(f"Records inserted: {insert_count}")
            print(f"Records skipped : {skip_count}")

            # if os.path.exists(csv_path):
            #     os.remove(csv_path)
            #     print(f"Deleted CSV file: {csv_path}")
            
            # if os.path.exists('results.xlsx'):
            #     os.remove('results.xlsx')
            #     print(f"Excel file also removed")
        

        except IntegrityError as e:
            session.rollback()
            print(f"Commit failed due to IntegrityError: {e}")

    except Exception as e:
        session.rollback()
        print(f"Unexpected error: {e}")
    finally:
        session.close()
