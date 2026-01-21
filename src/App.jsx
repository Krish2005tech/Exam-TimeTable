import React, { useState, useRef, useEffect } from 'react';
import { X, Edit2, Check, Download, Eye, EyeOff, Search } from 'lucide-react';
import * as htmlToImage from "html-to-image";

const ExamTimetableGenerator = () => {
  const timetableRef = useRef(null);
  const [examData, setExamData] = useState([]);
  const [dates, setDates] = useState({});
  const [slotTiming, setSlotTiming] = useState({});
  const [studentExams, setStudentExams] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [studentInfo, setStudentInfo] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [showClassrooms, setShowClassrooms] = useState(true);

  const colors = [
    '#E3F2FD', '#E8F5E9', '#F3E5F5', '#FFF9C4', '#FFECB3', 
    '#FFCDD2', '#F0F4C3', '#FFF3E0', '#E0E0E0', '#FFEBEE'
  ];

  useEffect(() => {
    fetch("/exam_schedule.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error("Failed to load exam_schedule.json");
        }
        return response.json();
      })
      .then((data) => {
        setExamData(data.exams || []);
        setDates(data.dates || {});
        setSlotTiming(data.slotTiming || {});
      })
      .catch((error) => {
        console.error("Error loading exam schedule:", error);
      });
  }, []);

  const searchStudent = () => {
    if (!searchTerm.trim()) return;

    const studentExamsList = examData.filter(exam => 
      exam.studentName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      exam.rollNo.toLowerCase().includes(searchTerm.toLowerCase())
    );

    if (studentExamsList.length > 0) {
      const student = studentExamsList[0];
      setStudentInfo({
        name: student.studentName,
        rollNo: student.rollNo,
        email: student.email,
        department: student.department,
        program: student.program
      });

      // Assign colors to exams
      const examsWithColors = studentExamsList.map((exam, index) => ({
        ...exam,
        id: Date.now() + index,
        color: colors[index % colors.length]
      }));

      setStudentExams(examsWithColors);
    } else {
      setStudentInfo(null);
      setStudentExams([]);
      alert('No exam records found for this student');
    }
  };

  const updateExam = (id, updates) => {
    setStudentExams(studentExams.map(exam => 
      exam.id === id ? { ...exam, ...updates } : exam
    ));
    setEditingId(null);
  };

  const removeExam = (id) => {
    setStudentExams(studentExams.filter(exam => exam.id !== id));
  };

  // const generateTimetable = () => {
  //   // Get sorted dates
  //   const sortedDates = Object.keys(dates).sort();
    
  //   // Group slots by day and time
  //   const slotsByDayTime = {};
  //   Object.entries(slotTiming).forEach(([slotName, slotInfo]) => {
  //     const key = `${slotInfo.day}-${slotInfo.start}`;
  //     if (!slotsByDayTime[key]) {
  //       slotsByDayTime[key] = {
  //         day: slotInfo.day,
  //         start: slotInfo.start,
  //         end: slotInfo.end,
  //         slots: []
  //       };
  //     }
  //     slotsByDayTime[key].slots.push(slotName);
  //   });

  //   // Get unique time slots sorted by start time
  //   const uniqueTimeSlots = Object.values(slotsByDayTime).sort((a, b) => {
  //     if (a.day !== b.day) return a.day - b.day;
  //     return timeToMinutes(a.start) - timeToMinutes(b.start);
  //   });

  //   // Remove duplicates based on day and time
  //   const timeSlots = [];
  //   const seen = new Set();
  //   uniqueTimeSlots.forEach(slot => {
  //     const key = `${slot.day}-${slot.start}-${slot.end}`;
  //     if (!seen.has(key)) {
  //       seen.add(key);
  //       timeSlots.push(slot);
  //     }
  //   });

  //   // Build timetable
  //   const timetable = {};
  //   sortedDates.forEach(date => {
  //     const dayNum = dates[date];
  //     timeSlots.forEach(timeSlot => {
  //       if (timeSlot.day === dayNum) {
  //         const key = `${date}-${timeSlot.start}-${timeSlot.end}`;
  //         timetable[key] = [];
  //       }
  //     });
  //   });

  //   // Fill timetable with exams
  //   studentExams.forEach(exam => {
  //     if (exam.slot && slotTiming[exam.slot]) {
  //       const slotInfo = slotTiming[exam.slot];
  //       const key = `${exam.date}-${slotInfo.start}-${slotInfo.end}`;
  //       if (timetable[key]) {
  //         timetable[key].push(exam);
  //       }
  //     }
  //   });

  //   return { sortedDates, timeSlots, timetable };
  // };


  const generateTimetable = () => {
  // Get sorted dates
  const sortedDates = Object.keys(dates).sort();
  
  // Get unique time slots (regardless of day)
  const uniqueTimeSlotsMap = {};
  Object.entries(slotTiming).forEach(([slotName, slotInfo]) => {
    const key = `${slotInfo.start}-${slotInfo.end}`;
    if (!uniqueTimeSlotsMap[key]) {
      uniqueTimeSlotsMap[key] = {
        start: slotInfo.start,
        end: slotInfo.end
      };
    }
  });

  // Convert to array and sort by start time
  const timeSlots = Object.values(uniqueTimeSlotsMap).sort((a, b) => {
    return timeToMinutes(a.start) - timeToMinutes(b.start);
  });

  // Build timetable
  const timetable = {};
  sortedDates.forEach(date => {
    timeSlots.forEach(timeSlot => {
      const key = `${date}-${timeSlot.start}-${timeSlot.end}`;
      timetable[key] = [];
    });
  });

  // Fill timetable with exams
  studentExams.forEach(exam => {
    if (exam.slot && slotTiming[exam.slot]) {
      const slotInfo = slotTiming[exam.slot];
      const key = `${exam.date}-${slotInfo.start}-${slotInfo.end}`;
      if (timetable[key]) {
        timetable[key].push(exam);
      }
    }
  });

  return { sortedDates, timeSlots, timetable };
};
  const timeToMinutes = (time) => {
    const match = time.match(/(\d+)(?::(\d+))?\s*(am|pm)/i);
    if (!match) return 0;
    let hours = parseInt(match[1]);
    const minutes = match[2] ? parseInt(match[2]) : 0;
    if (match[3].toLowerCase() === 'pm' && hours !== 12) hours += 12;
    if (match[3].toLowerCase() === 'am' && hours === 12) hours = 0;
    return hours * 60 + minutes;
  };

  const exportToPNG = async () => {
    if (!timetableRef.current) return;

    const node = timetableRef.current.cloneNode(true);
    Object.assign(node.style, {
      width: '1200px',
      height: 'auto',
      position: 'absolute',
      top: '0',
      left: '0',
      background: '#ffffff',
      overflow: 'visible',
    });

    document.body.appendChild(node);
    await document.fonts.ready;
    await new Promise((r) => requestAnimationFrame(r));

    const rect = node.getBoundingClientRect();
    const EXPORT_WIDTH = Math.ceil(rect.width);
    const EXPORT_HEIGHT = Math.ceil(rect.height);

    if (EXPORT_WIDTH === 0 || EXPORT_HEIGHT === 0) {
      console.error("Export failed: zero size");
      document.body.removeChild(node);
      return;
    }

    try {
      const dataUrl = await htmlToImage.toPng(node, {
        width: EXPORT_WIDTH,
        height: EXPORT_HEIGHT,
        pixelRatio: 2,
        backgroundColor: '#ffffff',
      });

      const link = document.createElement('a');
      link.download = 'exam-timetable.png';
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      document.body.removeChild(node);
    }
  };

  const { sortedDates, timeSlots, timetable } = generateTimetable();

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-red-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">Exam Timetable Generator</h1>
          <p className="text-gray-600">Find your personalized exam schedule</p>
        </div>

        {/* Search Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-800 mb-6">Search Your Schedule</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter your name or roll number..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && searchStudent()}
              className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none"
            />
            <button
              onClick={searchStudent}
              className="bg-gradient-to-r from-purple-500 to-pink-600 text-white px-8 py-3 rounded-lg font-semibold hover:shadow-lg transition flex items-center gap-2"
            >
              <Search size={20} /> Search
            </button>
          </div>

          {studentInfo && (
            <div className="mt-6 p-4 bg-gradient-to-r from-purple-100 to-pink-100 rounded-lg">
              <h3 className="font-bold text-gray-800 mb-2">Student Information</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                <p><span className="font-semibold">Name:</span> {studentInfo.name}</p>
                <p><span className="font-semibold">Roll No:</span> {studentInfo.rollNo}</p>
                <p><span className="font-semibold">Email:</span> {studentInfo.email}</p>
                <p><span className="font-semibold">Department:</span> {studentInfo.department}</p>
                <p><span className="font-semibold">Program:</span> {studentInfo.program}</p>
              </div>
            </div>
          )}
        </div>

        {/* Subject List */}
        {studentExams.length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
            <h2 className="text-2xl font-bold text-gray-800 mb-6">Subject List ({studentExams.length} exams)</h2>
            <div className="space-y-4">
              {studentExams.map(exam => (
                <ExamRow
                  key={exam.id}
                  exam={exam}
                  colors={colors}
                  slotTiming={slotTiming}
                  dates={dates}
                  isEditing={editingId === exam.id}
                  onEdit={() => setEditingId(exam.id)}
                  onUpdate={(updates) => updateExam(exam.id, updates)}
                  onRemove={() => removeExam(exam.id)}
                  onCancel={() => setEditingId(null)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Timetable Section */}
        {studentExams.length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-8 mb-8 overflow-x-auto">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-gray-800">Exam Schedule</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowClassrooms(!showClassrooms)}
                  className={`flex items-center gap-2 px-6 py-3 rounded-lg font-semibold transition ${
                    !showClassrooms
                      ? 'bg-gradient-to-r from-blue-500 to-cyan-600 text-white hover:shadow-lg'
                      : 'bg-gradient-to-r from-gray-400 to-gray-600 text-white hover:shadow'
                  }`}
                >
                  {showClassrooms ? <EyeOff size={20} /> : <Eye size={20} />}
                  {showClassrooms ? 'Hide Details' : 'Show Details'}
                </button>
                <button
                  onClick={exportToPNG}
                  className="flex items-center gap-2 bg-gradient-to-r from-purple-500 to-pink-600 text-white px-6 py-3 rounded-lg font-semibold hover:shadow-lg transition"
                >
                  <Download size={20} /> Export as PNG
                </button>
              </div>
            </div>
            <div ref={timetableRef} className="bg-white">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-purple-100">
                    <th className="border border-gray-300 p-3 text-gray-800 font-semibold text-center w-32">Time Slot</th>
                    {sortedDates.map(date => (
                      <th key={date} className="border border-gray-300 p-3 text-gray-800 font-semibold text-center">
                        <div className="flex flex-col">
                          <span className="text-sm">Day {dates[date]}</span>
                          <span className="text-xs">{new Date(date).toLocaleDateString('en-US', { weekday: 'short' })}</span>
                          <span className="font-bold">{new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
<tbody>
  {timeSlots.map((timeSlot, index) => {
    const timingDisplay = `${timeSlot.start} - ${timeSlot.end}`;
    
    return (
      <tr key={index}>
        <td className="border border-gray-300 p-3 text-gray-700 font-semibold text-center bg-gray-50">
          <div className="flex flex-col">
            <span className="text-xs text-gray-600">{timingDisplay}</span>
          </div>
        </td>
        {sortedDates.map(date => {
          const key = `${date}-${timeSlot.start}-${timeSlot.end}`;
          const cellExams = timetable[key] || [];
          
          if (cellExams.length === 0) {
            return (
              <td key={`${date}-${index}`} className="border border-gray-300 p-2 text-center min-h-20 bg-white">
                <div className="text-gray-300">-</div>
              </td>
            );
          }

          return (
            <td key={`${date}-${index}`} className="border border-gray-300 p-0 text-center">
              {cellExams.map(exam => (
                <div
                  key={exam.id}
                  className="text-sm font-bold w-full min-h-20 flex flex-col items-center justify-center p-2"
                  style={{ backgroundColor: exam.color }}
                >
                  <span className="text-gray-800 font-bold">{exam.courseName}</span>
                  <span className="text-gray-700 text-xs">{exam.courseCode}</span>
                  <span className="text-gray-600 text-xs">Slot: {exam.slot}</span>
                  {showClassrooms && (
                    <>
                      {exam.classroom && (
                        <span className="text-gray-600 text-xs">Room: {exam.classroom}</span>
                      )}
                      {exam.instructor && (
                        <span className="text-gray-600 text-xs">{exam.instructor}</span>
                      )}
                    </>
                  )}
                </div>
              ))}
            </td>
          );
        })}
      </tr>
    );
  })}
</tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

function ExamRow({ exam, colors, slotTiming, dates, isEditing, onEdit, onUpdate, onRemove, onCancel }) {
  const [courseName, setCourseName] = useState(exam.courseName);
  const [courseCode, setCourseCode] = useState(exam.courseCode);
  const [date, setDate] = useState(exam.date);
  const [slot, setSlot] = useState(exam.slot);
  const [classroom, setClassroom] = useState(exam.classroom || '');
  const [instructor, setInstructor] = useState(exam.instructor || '');
  const [color, setColor] = useState(exam.color);

  const handleSave = () => {
    onUpdate({
      courseName,
      courseCode,
      date,
      slot,
      classroom,
      instructor,
      color
    });
  };

  const sortedDates = Object.keys(dates).sort();

  if (isEditing) {
    return (
      <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Course Name</label>
            <input
              value={courseName}
              onChange={(e) => setCourseName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Course Code</label>
            <input
              value={courseCode}
              onChange={(e) => setCourseCode(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Date</label>
            <select
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            >
              {sortedDates.map(d => (
                <option key={d} value={d}>
                  Day {dates[d]} - {new Date(d).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Time Slot</label>
            <select
              value={slot}
              onChange={(e) => setSlot(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            >
              {Object.keys(slotTiming).map(s => (
                <option key={s} value={s}>
                  {s} (Day {slotTiming[s].day}: {slotTiming[s].start} - {slotTiming[s].end})
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Classroom</label>
            <input
              value={classroom}
              onChange={(e) => setClassroom(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-2">Instructor</label>
            <input
              value={instructor}
              onChange={(e) => setInstructor(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:border-purple-500 focus:outline-none text-sm"
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="text-xs font-semibold text-gray-600 block mb-2">Color</label>
          <div className="flex gap-2 flex-wrap">
            {colors.map(c => (
              <button
                key={c}
                onClick={() => setColor(c)}
                className={`w-8 h-8 rounded-lg border-2 ${color === c ? 'border-gray-800' : 'border-gray-300'}`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            className="flex-1 bg-green-500 text-white py-2 rounded-lg font-semibold hover:bg-green-600 transition flex items-center justify-center gap-2"
          >
            <Check size={18} /> Save
          </button>
          <button
            onClick={onCancel}
            className="flex-1 bg-gray-400 text-white py-2 rounded-lg font-semibold hover:bg-gray-500 transition"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  const slotInfo = slotTiming[exam.slot];
  const timing = slotInfo ? `${slotInfo.start} - ${slotInfo.end}` : '';

  return (
    <div
      className="border-l-4 rounded-lg p-6 flex justify-between items-center transition hover:shadow-md"
      style={{ backgroundColor: exam.color, borderColor: '#666' }}
    >
      <div className="text-left">
        <p className="font-bold text-gray-800">{courseName}</p>
        <p className="text-sm text-gray-700">
          {courseCode} • Day {dates[exam.date]} ({new Date(exam.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}) • Slot {exam.slot} ({timing})
          {exam.courseType && ` • ${exam.courseType}`}
        </p>
        {(classroom || instructor) && (
          <p className="text-xs text-gray-600 mt-1">
            {classroom && `Room: ${classroom}`}
            {classroom && instructor && ' • '}
            {instructor}
          </p>
        )}
      </div>
      <div className="flex gap-2">
        <button
          onClick={onEdit}
          className="bg-blue-500 text-white p-2 rounded-lg hover:bg-blue-600 transition"
        >
          <Edit2 size={18} />
        </button>
        <button
          onClick={onRemove}
          className="bg-red-500 text-white p-2 rounded-lg hover:bg-red-600 transition"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
}

export default ExamTimetableGenerator;