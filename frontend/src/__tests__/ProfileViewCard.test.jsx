import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import ProfileViewCard from '../components/ProfileViewCard';

const WELL_FORMED = {
  name: 'Ada Lovelace', intended_major: 'Computer Science',
  gpa_weighted: 4.4, gpa_unweighted: 3.95, sat_total: 1540, act_composite: 35,
  ap_exams: [{ subject: 'CS A', score: 5 }, { subject: 'Calc BC', score: 5 }],
  courses: [{ name: 'AP CS A', type: 'AP', grade_level: 11 }],
  extracurriculars: [{ name: 'Robotics', role: 'Captain', grades: '9-12' }],
  leadership_roles: [{ title: 'Robotics Captain' }, 'Class President'], // mixed obj/str
  awards: [{ name: 'Science Fair 1st', grade: 11 }],
  work_experience: [{ employer: 'Lab', role: 'Intern' }],
};

// The reported bug: array fields stored as STRING blobs (lengths show as counts,
// tabs .map() over them → crash/blank).
const MALFORMED = {
  intended_major: 'Computer Science',
  extracurriculars: 'x'.repeat(284),
  awards: 'y'.repeat(176),
};

describe('ProfileViewCard — defensive rendering', () => {
  it('renders well-formed data across all tabs', () => {
    render(<ProfileViewCard profileData={WELL_FORMED} />);
    // Overview counts
    expect(screen.getByText('AP Exams').previousSibling).toHaveTextContent('2');
    // Academics
    fireEvent.click(screen.getByRole('button', { name: /Academics/ }));
    expect(screen.getByText('AP CS A')).toBeInTheDocument();
    // Activities (+ mixed leadership renders without crashing)
    fireEvent.click(screen.getByRole('button', { name: /Activities/ }));
    expect(screen.getByText('Robotics')).toBeInTheDocument();
    expect(screen.getByText('Robotics Captain')).toBeInTheDocument();
    expect(screen.getByText('Class President')).toBeInTheDocument();
    // Achievements
    fireEvent.click(screen.getByRole('button', { name: /Achievements/ }));
    expect(screen.getByText('Science Fair 1st')).toBeInTheDocument();
  });

  it('shows sane counts for string-typed array fields (not character counts)', () => {
    render(<ProfileViewCard profileData={MALFORMED} />);
    // The bug showed the string LENGTH as a count (284 activities / 176 awards).
    expect(screen.queryByText('284')).not.toBeInTheDocument();
    expect(screen.queryByText('176')).not.toBeInTheDocument();
    // Overview "quick glance" counts should read 0 for the malformed fields.
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(2); // AP + activities + awards
  });

  it('does not crash on the Activities/Achievements tabs and surfaces the blob as text', () => {
    render(<ProfileViewCard profileData={MALFORMED} />);
    // Switching tabs must not throw (a string .map() would have crashed)
    fireEvent.click(screen.getByRole('button', { name: /Activities/ }));
    expect(screen.getByText('x'.repeat(284))).toBeInTheDocument();   // raw blob shown
    fireEvent.click(screen.getByRole('button', { name: /Achievements/ }));
    expect(screen.getByText('y'.repeat(176))).toBeInTheDocument();
  });

  it('handles a totally empty profile without crashing', () => {
    render(<ProfileViewCard profileData={{}} />);
    fireEvent.click(screen.getByRole('button', { name: /Academics/ }));
    expect(screen.getByText(/No courses added yet/)).toBeInTheDocument();
  });
});
