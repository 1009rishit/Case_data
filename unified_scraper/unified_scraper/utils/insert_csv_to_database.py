import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from Database.models import MetaData, HighCourt
from Database.high_court_database import SessionLocal
import os
import json



def insert_judgments_from_csv(csv_path: str, high_court_name: str, base_link: str):
    """
    Insert judgment metadata from CSV into DB, avoiding duplicates based on
    (case_id, document_link, high_court_id) combination.
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
    
    existing_case_ids = set()
    try:
        # Ensure High Court exists
        highcourt = session.query(HighCourt).filter_by(highcourt_name=high_court_name).first()
        
        existing_records: dict[str, list] = {}
        if not highcourt:
            highcourt = HighCourt(highcourt_name=high_court_name, base_link=base_link)
            session.add(highcourt)
            session.commit()
            session.refresh(highcourt)
            print(f"Added new High Court: {high_court_name}")

        rows: list[MetaData] = (
            session.query(MetaData.case_id, MetaData.document_link)
            .filter_by(high_court_id=highcourt.id)
            .all()
        )
        existing_records: dict[str, list] = {}
        for row in rows:
            val = row.document_link
            links = []
            if val:
                if isinstance(val, str):
                    try:
                        links = json.loads(val)
                    except Exception:
                        links = [val]
                elif isinstance(val, list):
                    links = val
            existing_records[row.case_id] = links

        existing_case_ids = set(existing_records.keys())
        insert_count = 0
        skip_count = 0

        for idx, row in df.iterrows():
            case_id = str(row['case_no']).strip() if pd.notna(row['case_no']) else None
            raw_date = str(row['date']).strip() if pd.notna(row['date']) else None
            #date_obj = datetime.strptime(raw_date, "%d-%m-%Y").date()
            party_detail = str(row['party']).strip() if pd.notna(row['party']) else None
            document_link = str(row['pdf_link']).strip() if pd.notna(row['pdf_link']) else None

            if not all([case_id, raw_date, party_detail, document_link]):
                print(f"Row {idx} skipped: Missing fields.")
                skip_count += 1
                continue
            
            if not raw_date:
                print(f" Row {idx} skipped: Invalid date '{raw_date}'.")
                skip_count += 1
                continue

            csv_links = existing_records.get(case_id, [])
            if document_link in csv_links:
                print(f"Row {idx} skipped: Duplicate document link for case_id '{case_id}' in CSV")
                skip_count += 1
                continue

            existing = session.query(MetaData).filter_by(
                high_court_id=highcourt.id,
                case_id=case_id
            ).first()

            if existing:
                links = []
                if existing.document_link:
                    if isinstance(existing.document_link, list):
                        links = existing.document_link
                    elif isinstance(existing.document_link, str):
                        try:
                            links = json.loads(existing.document_link)
                        except Exception:
                            links = [existing.document_link]

                if document_link in links:
                    print(f"Row {idx} skipped: Duplicate document link in DB for case_id '{case_id}'")
                    skip_count += 1
                    continue

                links.append(document_link)
                existing.document_link = json.dumps(links)
                session.add(existing)
                insert_count += 1

            else:
                
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

            if case_id in existing_records:
                existing_records[case_id].append(document_link)
            else:
                existing_records[case_id] = [document_link]

        try:
            session.commit()
            print(f"\n Migration completed.")
            print(f" Records inserted: {insert_count}")
            print(f" Records skipped : {skip_count}")

            if os.path.exists(csv_path):
                os.remove(csv_path)
                print(f"Deleted CSV file: {csv_path}")

        except IntegrityError as e:
            session.rollback()
            print(f"Commit failed due to IntegrityError: {e}")

    except Exception as e:
        session.rollback()
        print(f" Unexpected error: {e}")
    finally:
        session.close()


