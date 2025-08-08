import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database.models import MetaData, HighCourt
from database.high_court_database import SessionLocal


def clean_date(raw_date: str):
    """
    Cleans and parses a date string, removing trailing '(pdf)' and other suffixes.
    Returns a `date` object or None if invalid.
    """
    try:
        if pd.isna(raw_date) or not raw_date.strip():
            raise ValueError("Empty or NaN date")
        cleaned = raw_date.replace("(pdf)", "").strip().split()[0]
        return datetime.strptime(cleaned, '%d-%m-%Y').date()
    except Exception as e:
        print(f" Failed to parse date '{raw_date}': {e}")
        return None


def insert_judgment_from_csv(csv_path: str):
    # Step 1: Load CSV
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Failed to read CSV file '{csv_path}': {e}")
        return

    # Step 2: Validate required columns
    required_columns = ['case_no', 'date', 'party', 'pdf_link']
    if not all(col in df.columns for col in required_columns):
        missing = [col for col in required_columns if col not in df.columns]
        print(f"Missing columns in CSV: {missing}")
        return

    df = df[required_columns]
    print(f"Loaded {len(df)} rows from '{csv_path}'")
    print(f"Columns: {df.columns.tolist()}")

    session: Session = SessionLocal()
    fixed_scraped_at = datetime.strptime("2025/08/07 10:43", "%Y/%m/%d %H:%M")

    try:
        # Step 3: Ensure High Court exists
        highcourt = session.query(HighCourt).filter_by(highcourt_name="Delhi High Court").first()
        if not highcourt:
            highcourt = HighCourt(
                highcourt_name="Delhi High Court",
                base_link="https://delhihighcourt.nic.in"
            )
            session.add(highcourt)
            session.commit()
            session.refresh(highcourt)

        insert_count = 0
        skip_count = 0

        #  Preload all existing case_ids for this court to avoid duplicates
        existing_case_ids = set(
            session.query(MetaData.case_id)
            .filter_by(high_court_id=highcourt.id)
            .with_entities(MetaData.case_id)
            .all()
        )
        existing_case_ids = {case_id for (case_id,) in existing_case_ids}

        for index, row in df.iterrows():
            case_id = str(row['case_no']).strip() if pd.notna(row['case_no']) else None
            raw_date = str(row['date']).strip() if pd.notna(row['date']) else None
            party_detail = str(row['party']).strip() if pd.notna(row['party']) else None
            document_link = str(row['pdf_link']).strip() if pd.notna(row['pdf_link']) else None

            if not all([case_id, raw_date, party_detail, document_link]):
                print(f" Row {index} skipped: Missing required fields.")
                skip_count += 1
                continue

            judgement_date = clean_date(raw_date)
            if not judgement_date:
                print(f" Row {index} skipped: Invalid date '{raw_date}'.")
                skip_count += 1
                continue

            if case_id in existing_case_ids:
                print(f"\n Row {index} skipped: Duplicate case_id '{case_id}'")

                # 🔍 Fetch and display original DB entry
                original = session.query(MetaData).filter_by(
                    high_court_id=highcourt.id,
                    case_id=case_id
                ).first()

                if original:
                    print(" Existing DB Entry:")
                    print(f"   case_id       : {original.case_id}")
                    print(f"   judgement_date: {original.judgement_date}")
                    print(f"   party_detail  : {original.party_detail}")
                    print(f"   document_link : {original.document_link}")

                # Show the new incoming (duplicate) entry
                print("Duplicate CSV Entry:")
                print(f"   case_id       : {case_id}")
                print(f"   judgement_date: {judgement_date}")
                print(f"   party_detail  : {party_detail}")
                print(f"   document_link : {document_link}")
                skip_count += 1
                continue

            # Insert new metadata record
            metadata = MetaData(
                high_court_id=highcourt.id,
                case_id=case_id,
                judgement_date=judgement_date,
                party_detail=party_detail,
                document_link=document_link,
                scrapped_at=fixed_scraped_at,
                is_downloaded=True
            )
            session.add(metadata)
            existing_case_ids.add(case_id)  # Add to avoid duplicates in the same batch
            insert_count += 1

        # Final commit
        try:
            session.commit()
            print(f"\nMigration completed.")
            print(f" Records inserted: {insert_count}")
            print(f"Records skipped : {skip_count}")
        except IntegrityError as e:
            session.rollback()
            print(f"Commit failed due to IntegrityError: {e}")

    except Exception as e:
        session.rollback()
        print(f"Unexpected error during migration: {e}")

    finally:
        session.close()
