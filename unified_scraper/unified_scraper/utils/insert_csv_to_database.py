import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from Database.models import MetaData, HighCourt
from Database.high_court_database import SessionLocal


def clean_date(raw_date: str):
    """Parse and clean date strings like '01-01-2025 (pdf)' -> datetime.date"""
    if pd.isna(raw_date) or not str(raw_date).strip():
        return None
    try:
        cleaned = str(raw_date).replace("(pdf)", "").strip().split()[0]
        return datetime.strptime(cleaned, '%d-%m-%Y').date()
    except ValueError:
        return None


def insert_judgments_from_csv(csv_path: str, high_court_name: str, base_link: str):
    """
    Insert judgment metadata from CSV into DB, avoiding duplicates based on
    (case_id, document_link, high_court_id) combination.
    """
    # 1️⃣ Load CSV
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
        highcourt = session.query(HighCourt).filter_by(highcourt_name=high_court_name).first()
        if not highcourt:
            highcourt = HighCourt(highcourt_name=high_court_name, base_link=base_link)
            session.add(highcourt)
            session.commit()
            session.refresh(highcourt)
            print(f"Added new High Court: {high_court_name}")

        existing_records = {
            (cid, dlink)
            for cid, dlink in session.query(MetaData.case_id, MetaData.document_link)
            .filter_by(high_court_id=highcourt.id)
            .all()
        }
        existing_case_ids = {cid for cid, _ in existing_records}

        insert_count = 0
        skip_count = 0

        # 2️⃣ Process CSV rows
        for idx, row in df.iterrows():
            case_id = str(row['case_no']).strip() if pd.notna(row['case_no']) else None
            raw_date = str(row['date']).strip() if pd.notna(row['date']) else None
            party_detail = str(row['party']).strip() if pd.notna(row['party']) else None
            document_link = str(row['pdf_link']).strip() if pd.notna(row['pdf_link']) else None

            # Skip rows with missing required data
            if not all([case_id, raw_date, party_detail, document_link]):
                print(f"Row {idx} skipped: Missing fields.")
                skip_count += 1
                continue

            # Validate date
            judgement_date = clean_date(raw_date)
            if not judgement_date:
                print(f" Row {idx} skipped: Invalid date '{raw_date}'.")
                skip_count += 1
                continue

            # Skip if exact record already exists
            if (case_id, document_link) in existing_records:
                print(f"Row {idx} skipped: Duplicate case_id '{case_id}' with same document_link.")
                skip_count += 1
                continue

            # Warn if case_id exists but with different link
            if case_id in existing_case_ids:
                print(f" Case ID '{case_id}' exists with a different document_link — inserting anyway.")

            # Create MetaData entry
            metadata = MetaData(
                high_court_id=highcourt.id,
                case_id=case_id,
                judgement_date=judgement_date,
                party_detail=party_detail,
                document_link=document_link,
                scrapped_at=datetime.now(),
                is_downloaded=False
            )
            session.add(metadata)

            # Update in-memory sets to avoid future duplicates
            existing_records.add((case_id, document_link))
            existing_case_ids.add(case_id)
            insert_count += 1

        # Commit changes
        try:
            session.commit()
            print(f"\n Migration completed.")
            print(f" Records inserted: {insert_count}")
            print(f" Records skipped : {skip_count}")
        except IntegrityError as e:
            session.rollback()
            print(f"Commit failed due to IntegrityError: {e}")

    except Exception as e:
        session.rollback()
        print(f" Unexpected error: {e}")
    finally:
        session.close()


