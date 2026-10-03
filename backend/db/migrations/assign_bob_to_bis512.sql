-- Assign Bob to BIS512 (Financing Economic Development).
-- This migration is intentionally separate from the original seed migration so
-- existing databases can move Bob off the placeholder MATH416 course.

DELETE FROM roadmap_cache
WHERE student_id = 'b0000002-0000-4000-8000-000000000002';

DELETE FROM roadmap_position
WHERE student_id = 'b0000002-0000-4000-8000-000000000002';

DELETE FROM student_courses
WHERE student_id = 'b0000002-0000-4000-8000-000000000002';

INSERT INTO student_courses (student_id, course_id)
VALUES ('b0000002-0000-4000-8000-000000000002', 'BIS512');
