import pandas as pd
import json
from dateutil import parser
import re


def format_time(dt):
    hour = dt.strftime('%I').lstrip('0')  # remove leading zero
    suffix = dt.strftime('%p').lower()
    return f"{hour}{suffix}"

def extract_time_range(time_val):
    """Robust parser for multiple time formats"""
    try:
        if pd.isna(time_val):
            return None, None

        time_str = str(time_val).lower().strip()

        # Normalize separators → replace 'to' with '-'
        time_str = re.sub(r'\s+to\s+', '-', time_str)

        # Now split
        parts = time_str.split('-')
        if len(parts) != 2:
            return None, None

        start = parser.parse(parts[0].strip())
        end = parser.parse(parts[1].strip())

        return (
            format_time(start),
            format_time(end)
            )

    except Exception as e:
        return None, None


def convert_excel_to_json(excel_file_path, output_json_path='exam_schedule.json'):
    print(f"Reading Excel file: {excel_file_path}")

    df = pd.read_excel(excel_file_path)
    df.columns = df.columns.str.strip()

    # ✅ Required columns check
    required_cols = ['Roll No', 'Student Name', 'Course Code', 'Course Name', 'Date', 'Slot']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ✅ Time column is mandatory for slot inference
    if 'Time' not in df.columns:
        raise ValueError("❌ 'Time' column is required to infer slot timings")

    print("\nAvailable columns:")
    for col in df.columns:
        print(f" - {col}")

    # ✅ Clean data
    df = df.dropna(subset=required_cols)
    df = df.drop_duplicates()

    # ✅ Safe date parsing
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

    # ✅ Normalize slot labels
    df['Slot'] = df['Slot'].astype(str).str.strip().str.upper()

    # ✅ Extract unique dates
    dates = sorted(df['Date'].unique().tolist())
    print(f"\nFound {len(dates)} exam dates")

    # =========================================================
    # 🔥 SLOT TIMING INFERENCE (CORE FIX)
    # =========================================================
    print("\nInferring slot timings from data...")

    slot_timing = {}

    for row in df.to_dict(orient='records'):
        slot = row['Slot']
        time_val = row['Time']

        if slot in slot_timing:
            # 🔍 Conflict detection
            start, end = extract_time_range(time_val)
            if start and end:
                existing = slot_timing[slot]
                if existing['start'] != start or existing['end'] != end:
                    print(f"❌ Conflict for slot {slot}:")
                    print(f"   Existing: {existing['start']} - {existing['end']}")
                    print(f"   New:      {start} - {end}")
            continue

        # First time seeing this slot → infer timing
        start, end = extract_time_range(time_val)

        if start and end:
            slot_timing[slot] = {
                'start': start,
                'end': end
            }
            print(f"  Slot {slot}: {start} - {end}")
        else:
            print(f"⚠️ Could not parse time for slot {slot}")

    # =========================================================
    # 📦 BUILD EXAM LIST
    # =========================================================
    exams = []

    for row in df.to_dict(orient='records'):
        exam = {
            'rollNo': str(row['Roll No']).strip(),
            'studentName': str(row['Student Name']).strip(),
            'email': '' if pd.isna(row.get('Email')) else str(row['Email']).strip(),
            'courseCode': str(row['Course Code']).strip(),
            'courseName': str(row['Course Name']).strip(),
            'slot': row['Slot'],
            'date': row['Date'],
            'department': str(row.get('Department', 'N/A')).strip() if pd.notna(row.get('Department')) else 'N/A',
            'program': str(row.get('Program', 'N/A')).strip() if pd.notna(row.get('Program')) else 'N/A',
        }

        # Optional fields
        if pd.notna(row.get('Instructor 1')):
            exam['instructor'] = str(row['Instructor 1']).strip()

        if pd.notna(row.get('Classroom')):
            exam['classroom'] = str(row['Classroom']).strip()

        if pd.notna(row.get('Course Type')):
            exam['courseType'] = str(row['Course Type']).strip()

        exams.append(exam)

    # =========================================================
    # 📄 FINAL OUTPUT
    # =========================================================
    output_data = {
        'dates': dates,
        'slotTiming': slot_timing,
        'exams': exams
    }

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Conversion complete!")
    print(f"📄 Output file: {output_json_path}")
    print(f"📊 Total records: {len(exams)}")
    print(f"👥 Unique students: {len(df['Roll No'].unique())}")
    print(f"📚 Unique courses: {len(df['Course Code'].unique())}")
    print(f"⏰ Slots inferred: {len(slot_timing)}")

    return output_data


def print_sample_student(json_file_path='exam_schedule.json'):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not data['exams']:
        print("No exam data found.")
        return

    first_roll = data['exams'][0]['rollNo']
    student_exams = [e for e in data['exams'] if e['rollNo'] == first_roll]

    print(f"\n📋 Sample Schedule for Roll No: {first_roll}")
    print(f"Student: {student_exams[0]['studentName']}")
    print(f"Total Exams: {len(student_exams)}\n")

    for exam in student_exams:
        slot = exam['slot']
        timing = data['slotTiming'].get(slot, {'start': '?', 'end': '?'})

        print(f"  • {exam['courseName']} ({exam['courseCode']})")
        print(f"    Date: {exam['date']} | Slot: {slot} | {timing['start']} - {timing['end']}")

        if 'classroom' in exam:
            print(f"    Classroom: {exam['classroom']}")

        print()


if __name__ == "__main__":
    excel_file = "exam_data.xlsx"
    output_file = "exam_schedule.json"

    try:
        convert_excel_to_json(excel_file, output_file)
        print_sample_student(output_file)

    except FileNotFoundError:
        print(f"❌ File '{excel_file}' not found!")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()