import pandas as pd
import json
from datetime import datetime

def convert_excel_to_json(excel_file_path, output_json_path='exam_schedule.json'):
    """
    Convert Excel file to JSON format for exam timetable
    
    Expected Excel columns:
    - Date
    - Time
    - Roll No
    - Student Name
    - Email
    - Course Code
    - Course Name
    - Course Type
    - Slot
    - Instructor 1
    - Instructor 1 Email
    - Student Category
    - Department
    - Program
    - Registered As
    """
    
    # Read Excel file
    print(f"Reading Excel file: {excel_file_path}")
    df = pd.read_excel(excel_file_path)
    
    # Clean column names (remove extra spaces)
    df.columns = df.columns.str.strip()
    
    # Display available columns
    print("\nAvailable columns in Excel:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. {col}")
    
    # Remove rows with missing critical data
    df = df.dropna(subset=['Roll No', 'Student Name', 'Course Code', 'Course Name', 'Date', 'Slot'])
    
    # Convert Date to string format (YYYY-MM-DD)
    df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
    
    # Get unique dates sorted
    dates = sorted(df['Date'].unique().tolist())
    print(f"\nFound {len(dates)} exam dates")
    
    # Manual slot timing definition
    # You can modify these timings as per your institution's schedule
    slot_timing = {
        'A': {'start': '9am', 'end': '12pm'},
        'B': {'start': '2pm', 'end': '5pm'},
        'C': {'start': '9am', 'end': '11am'},
        'D': {'start': '11am', 'end': '1pm'},
        'E': {'start': '2pm', 'end': '4pm'},
        'F': {'start': '4pm', 'end': '6pm'},
        'FN': {'start': '9am', 'end': '12pm'},
        'AN': {'start': '2pm', 'end': '5pm'},
    }
    
    # If Time column exists, try to extract timing from it
    if 'Time' in df.columns:
        print("\nDetected Time column. Extracting slot timings...")
        for slot in df['Slot'].unique():
            if pd.notna(slot) and slot not in slot_timing:
                # Get first occurrence of this slot
                time_val = df[df['Slot'] == slot]['Time'].iloc[0]
                if pd.notna(time_val):
                    # Try to parse time (assuming format like "9:00 AM - 12:00 PM")
                    try:
                        parts = str(time_val).split('-')
                        if len(parts) == 2:
                            start_time = parts[0].strip().lower().replace(':00', '').replace(' ', '')
                            end_time = parts[1].strip().lower().replace(':00', '').replace(' ', '')
                            slot_timing[slot] = {
                                'start': start_time,
                                'end': end_time
                            }
                            print(f"  Slot {slot}: {start_time} - {end_time}")
                    except:
                        pass
    
    # Get unique slots and ensure they're in slot_timing
    unique_slots = df['Slot'].unique()
    for slot in unique_slots:
        if pd.notna(slot) and slot not in slot_timing:
            print(f"Warning: Slot '{slot}' not defined in slot_timing. Using default 9am-12pm")
            slot_timing[slot] = {'start': '9am', 'end': '12pm'}
    
    # Build exams list
    exams = []
    for _, row in df.iterrows():
        exam = {
            'rollNo': str(row['Roll No']).strip(),
            'studentName': str(row['Student Name']).strip(),
            'email': str(row['Email']).strip() if pd.notna(row['Email']) else '',
            'courseCode': str(row['Course Code']).strip(),
            'courseName': str(row['Course Name']).strip(),
            'slot': str(row['Slot']).strip(),
            'date': row['Date'],
            'department': str(row['Department']).strip() if 'Department' in df.columns and pd.notna(row['Department']) else 'N/A',
            'program': str(row['Program']).strip() if 'Program' in df.columns and pd.notna(row['Program']) else 'N/A',
        }
        
        # Optional fields
        if 'Instructor 1' in df.columns and pd.notna(row['Instructor 1']):
            exam['instructor'] = str(row['Instructor 1']).strip()
        
        # Add classroom if available (you might need to add this column or extract from another field)
        if 'Classroom' in df.columns and pd.notna(row['Classroom']):
            exam['classroom'] = str(row['Classroom']).strip()
        
        if 'Course Type' in df.columns and pd.notna(row['Course Type']):
            exam['courseType'] = str(row['Course Type']).strip()
        
        exams.append(exam)
    
    # Create final JSON structure
    output_data = {
        'dates': dates,
        'slotTiming': slot_timing,
        'exams': exams
    }
    
    # Write to JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Successfully converted Excel to JSON!")
    print(f"📄 Output file: {output_json_path}")
    print(f"📊 Total exam records: {len(exams)}")
    print(f"👥 Unique students: {len(df['Roll No'].unique())}")
    print(f"📚 Unique courses: {len(df['Course Code'].unique())}")
    print(f"📅 Exam dates: {len(dates)}")
    print(f"⏰ Time slots: {len(slot_timing)}")
    
    return output_data


def print_sample_student(json_file_path='exam_schedule.json'):
    """
    Print a sample student's exam schedule for verification
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if data['exams']:
        # Get first student
        first_student_roll = data['exams'][0]['rollNo']
        student_exams = [e for e in data['exams'] if e['rollNo'] == first_student_roll]
        
        print(f"\n📋 Sample Schedule for Roll No: {first_student_roll}")
        print(f"Student: {student_exams[0]['studentName']}")
        print(f"Total Exams: {len(student_exams)}\n")
        
        for exam in student_exams:
            print(f"  • {exam['courseName']} ({exam['courseCode']})")
            print(f"    Date: {exam['date']} | Slot: {exam['slot']} | {data['slotTiming'][exam['slot']]['start']} - {data['slotTiming'][exam['slot']]['end']}")
            if 'classroom' in exam:
                print(f"    Classroom: {exam['classroom']}")
            print()


if __name__ == "__main__":
    # Example usage
    excel_file = "exam_data.xlsx"  # Change this to your Excel file path
    output_file = "exam_schedule.json"
    
    try:
        # Convert Excel to JSON
        convert_excel_to_json(excel_file, output_file)
        
        # Print sample student schedule
        print_sample_student(output_file)
        
    except FileNotFoundError:
        print(f"❌ Error: File '{excel_file}' not found!")
        print("Please ensure the Excel file is in the same directory as this script.")
    except Exception as e:
        print(f"❌ Error occurred: {str(e)}")
        import traceback
        traceback.print_exc()