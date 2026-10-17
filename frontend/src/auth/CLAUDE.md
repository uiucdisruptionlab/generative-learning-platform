# Student Identity

There is no real authentication yet. A "login" is a persona name mapped to a fixed student UUID, and that UUID is what every backend call sends.

The UUIDs in `PERSONA_STUDENT_IDS` must match the rows in `backend/db/seed_students.sql`. Change both together, or the persona will load an empty profile.

An unknown persona string is passed through unchanged as the student id.
