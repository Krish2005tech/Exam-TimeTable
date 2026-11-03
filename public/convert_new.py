import pandas as pd
import json
import re
from collections import OrderedDict
from dateutil import parser

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
NAMES_FILE = "names.xlsx"          # student-level data (Roll No, Course Code, Slot, ...)
VENUE_FILE = "exam_venue_flat.xlsx"  # flattened venue sheet (one row per course per room)
OUTPUT_FILE = "exam_schedule.json"


# ---------------------------------------------------------------------------
# TIME HELPERS (unchanged behaviour from convert.py)
# ---------------------------------------------------------------------------
def format_time(dt):
    hour = dt.strftime('%I').lstrip('0')
    suffix = dt.strftime('%p').lower()
    return f"{hour}{suffix}"


def extract_time_range(time_val):
    """Robust parser for multiple time formats"""
    try:
        if pd.isna(time_val):
            return None, None
        time_str = str(time_val).lower().strip()
        time_str = re.sub(r'\s+to\s+', '-', time_str)
        parts = time_str.split('-')
        if len(parts) != 2:
            return None, None
        start = parser.parse(parts[0].strip())
        end = parser.parse(parts[1].strip())
        return format_time(start), format_time(end)
    except Exception:
        return None, None


def _start_key(time_val):
    """Normalised start time (e.g. '9am') used to match venue sessions with names.xlsx."""
    start, _ = extract_time_range(time_val)
    return start


# ---------------------------------------------------------------------------
# VENUE READER  (reads the flattened sheet: one row per course per room)
# ---------------------------------------------------------------------------
def _clean(s):
    return re.sub(r'\s+', ' ', str(s)).strip()


def read_venue_workbook(path):
    """
    Reads exam_venue_flat.xlsx (columns: Date, Time, Course Code, Course Name,
    Department, Room, ...). Returns a DataFrame with:
        date (YYYY-MM-DD), time_raw, start, courseCode, block, room
    """
    flat = pd.read_excel(path)
    flat.columns = flat.columns.str.strip()

    needed = ['Date', 'Time', 'Course Code', 'Department', 'Room']
    missing = [c for c in needed if c not in flat.columns]
    if missing:
        raise ValueError(f"Venue file is missing columns: {missing}")

    flat = flat.dropna(subset=['Date', 'Course Code'])

    venue = pd.DataFrame({
        'date': pd.to_datetime(flat['Date'], errors='coerce').dt.strftime('%Y-%m-%d'),
        'time_raw': flat['Time'].astype(str).str.strip(),
        'courseCode': flat['Course Code'].astype(str).str.strip(),
        'block': flat['Department'].apply(lambda x: '' if pd.isna(x) else _clean(x)),
        'room': flat['Room'].apply(
            lambda r: '' if pd.isna(r)
            else str(int(r)) if isinstance(r, float) and float(r).is_integer()
            else str(r).strip()),
    })
    venue = venue.dropna(subset=['date'])
    venue['start'] = venue['time_raw'].apply(_start_key)
    return venue


def build_classroom_lookup(venue):
    """
    {(date, courseCode): [ (start, "classroom string"), ... ]}
    A course in several rooms gets them joined, grouped by block, e.g.
        "Lecture Hall Complex-1 (Old LHC): 105, 106, 204"
    """
    lookup = {}
    for (date, code, start), g in venue.groupby(['date', 'courseCode', 'start'], dropna=False):
        by_block = OrderedDict()
        for _, r in g.iterrows():
            by_block.setdefault(r['block'], [])
            if r['room'] and r['room'] not in by_block[r['block']]:
                by_block[r['block']].append(r['room'])
        text = '; '.join(f"{b}: {', '.join(rooms)}" for b, rooms in by_block.items() if rooms)
        lookup.setdefault((date, code), []).append((start, text))
    return lookup


def find_classroom(lookup, date, code, time_val):
    options = lookup.get((date, code))
    if not options:
        return None
    if len(options) == 1:
        return options[0][1]
    # Same course on same date in >1 session -> match by start time
    s = _start_key(time_val)
    for start, text in options:
        if start == s:
            return text
    return options[0][1]


# ---------------------------------------------------------------------------
# MAIN CONVERSION
# ---------------------------------------------------------------------------
def convert_excel_to_json(names_path=NAMES_FILE, venue_path=VENUE_FILE,
                          output_json_path=OUTPUT_FILE):
    print(f"Reading names file : {names_path}")
    df = pd.read_excel(names_path)
    df.columns = df.columns.str.strip()

    required_cols = ['Roll No', 'Student Name', 'Course Code', 'Course Name', 'Date', 'Slot']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if 'Time' not in df.columns:
        raise ValueError("❌ 'Time' column is required to infer slot timings")

    print("\nAvailable columns:")
    for col in df.columns:
        print(f" - {col}")

    df = df.dropna(subset=required_cols)
    df = df.drop_duplicates()

    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

    df['Slot'] = df['Slot'].astype(str).str.strip().str.upper()
    df['Course Code'] = df['Course Code'].astype(str).str.strip()

    dates = sorted(df['Date'].unique().tolist())
    print(f"\nFound {len(dates)} exam dates")

    # ---- Slot timing inference (same as before) ----
    print("\nInferring slot timings from data...")
    slot_timing = {}
    for row in df.to_dict(orient='records'):
        slot = row['Slot']
        start, end = extract_time_range(row['Time'])
        if slot in slot_timing:
            if start and end:
                existing = slot_timing[slot]
                if existing['start'] != start or existing['end'] != end:
                    print(f"❌ Conflict for slot {slot}:")
                    print(f"   Existing: {existing['start']} - {existing['end']}")
                    print(f"   New:      {start} - {end}")
            continue
        if start and end:
            slot_timing[slot] = {'start': start, 'end': end}
            print(f"  Slot {slot}: {start} - {end}")
        else:
            print(f"⚠️ Could not parse time for slot {slot}")

    # ---- Venue lookup ----
    print(f"\nReading venue file : {venue_path}")
    venue = read_venue_workbook(venue_path)
    lookup = build_classroom_lookup(venue)
    print(f"  {len(venue)} venue rows, {len(lookup)} (date, course) pairs")

    # ---- Build exam list (same keys as convert.py) ----
    exams = []
    unmatched = set()

    for row in df.to_dict(orient='records'):
        exam = {
            'rollNo': str(row['Roll No']).strip(),
            'studentName': str(row['Student Name']).strip(),
            'email': '' if pd.isna(row.get('Email')) else str(row['Email']).strip(),
            'courseCode': row['Course Code'],
            'courseName': str(row['Course Name']).strip(),
            'slot': row['Slot'],
            'date': row['Date'],
            'department': str(row.get('Department', 'N/A')).strip() if pd.notna(row.get('Department')) else 'N/A',
            'program': str(row.get('Program', 'N/A')).strip() if pd.notna(row.get('Program')) else 'N/A',
        }

        if pd.notna(row.get('Instructor 1')):
            exam['instructor'] = str(row['Instructor 1']).strip()

        # Classroom now comes from the venue workbook (falls back to a
        # 'Classroom' column in names.xlsx if you ever add one)
        classroom = find_classroom(lookup, row['Date'], row['Course Code'], row['Time'])
        if classroom:
            exam['classroom'] = classroom
        elif pd.notna(row.get('Classroom')):
            exam['classroom'] = str(row['Classroom']).strip()
        else:
            unmatched.add((row['Date'], row['Course Code']))

        if pd.notna(row.get('Course Type')):
            exam['courseType'] = str(row['Course Type']).strip()

        exams.append(exam)

    output_data = {'dates': dates, 'slotTiming': slot_timing, 'exams': exams}

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Conversion complete!")
    print(f"📄 Output file: {output_json_path}")
    print(f"📊 Total records: {len(exams)}")
    print(f"👥 Unique students: {len(df['Roll No'].unique())}")
    print(f"📚 Unique courses: {len(df['Course Code'].unique())}")
    print(f"⏰ Slots inferred: {len(slot_timing)}")
    print(f"🏫 Records with classroom: {sum('classroom' in e for e in exams)}/{len(exams)}")
    if unmatched:
        print(f"\n⚠️ {len(unmatched)} (date, course) pairs had no venue match:")
        for d, c in sorted(unmatched):
            print(f"   {d}  {c}")

    return output_data


def print_sample_student(json_file_path=OUTPUT_FILE):
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
        timing = data['slotTiming'].get(exam['slot'], {'start': '?', 'end': '?'})
        print(f"  • {exam['courseName']} ({exam['courseCode']})")
        print(f"    Date: {exam['date']} | Slot: {exam['slot']} | {timing['start']} - {timing['end']}")
        if 'classroom' in exam:
            print(f"    Classroom: {exam['classroom']}")
        print()


if __name__ == "__main__":
    try:
        convert_excel_to_json(NAMES_FILE, VENUE_FILE, OUTPUT_FILE)
        print_sample_student(OUTPUT_FILE)
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
