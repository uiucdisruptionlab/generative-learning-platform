# System Architecture

This document describes the full architecture of the learner agent platform — a personalized, adaptive learning system. It is intended to give an AI coding agent full context on the system before implementing any feature.

---

## High-Level Overview

The system teaches students through an interactive lesson loop. It uses a knowledge graph to structure curriculum, an LLM to generate and deliver content, and spaced repetition to schedule reviews.

- **Frontend:** React (hardcoded lesson UI, content block rendering)
- **Backend:** FastAPI (Python)
- **Graph DB:** Neo4j (curriculum structure and content chunks)
- **Relational DB:** Supabase (persistent learner state)
- **LLM:** AWS Bedrock. Example call in python:

'''
 client = create_bedrock_runtime_client(region=AWS_REGION)
    response = client.converse(
        modelId=MODEL_ID,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"type": "text", "text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
'''

---

## Current State — What Is and Isn't Connected

This is critical context before touching any code. Several components exist but are not wired together.

### What exists and works
- Neo4j graph populated with Course, Lecture, Chunk, Concept nodes and all edges
- PDF ingestion pipeline (chunks written to Neo4j)
- Concept extraction from chunks
- Roadmap / topo sort generation — **but only runs as a standalone script, not via any API endpoint**
- Hardcoded frontend lesson UI
- `students`, `roadmap_position`, `srs_records` tables created in Supabase
- `students` table populated with three student personas (Alice, Bob, Charles)

### What is not yet connected or built
- `roadmap_position` and `srs_records` are empty — no data has been loaded
- No API endpoints exist for roadmap generation, session start, or lesson loop
- Content generation loop exists but is broken — see Content Generation Loop section for what's wrong and how to fix it
- No SRS scheduling or write-back
- No scoring logic

---

## Neo4j — Knowledge Graph

Stores the full curriculum structure. No learner data lives here.

### Node types

| Node | Properties | Purpose |
|------|-----------|---------|
| `Course` | id, title, description | Top-level course |
| `Lecture` | id, title, order | A lecture within a course |
| `Chunk` | id, text, index | A content chunk from a lecture |
| `Concept` | id, name, description | An atomic learning concept extracted from chunks |

### Relationships

| Relationship | From → To | Purpose |
|-------------|----------|---------|
| `HAS_LECTURE` | Course → Lecture | A course contains lectures |
| `HAS_CHUNK` | Lecture → Chunk | A lecture contains content chunks |
| `CONTAINS` | Chunk → Concept | A chunk references a concept |
| `PREREQUISITE_OF` | Concept → Concept | Used for topo sort to order the roadmap |
| `PART_OF` | Concept ↔ Concept | Concept is a sub-part of another |
| `RELATED_TO` | Concept ↔ Concept | Soft relationship for suggestions |

### Key queries

**Fetch chunks for a concept:**
```cypher
MATCH (ch:Chunk)-[:CONTAINS]->(c:Concept {id: $concept_id})
RETURN ch.text ORDER BY ch.index
```

**Topo sort for roadmap generation — run on every session start:**
```cypher
MATCH (c:Concept)
OPTIONAL MATCH (c)-[:PREREQUISITE_OF]->(prereq:Concept)
RETURN c.id, collect(prereq.id) as prerequisites
```
Then run Kahn's algorithm in Python on the result to get an ordered list of concept IDs.

---

## Supabase — Persistent Learner State

There is no caching layer. The roadmap is generated fresh from Neo4j on every session start by running the topo sort query. Supabase only stores durable learner state.

### `students` (populated, do not modify schema)

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text | |
| academic_level | text | |
| major_or_field | text | |
| learning_goals | jsonb | `{ primary_focus, coding_experience, topic_familiarity }` |
| interests | text[] | |
| weekly_hours | integer | |
| preferred_formats | text[] | `["videos", "flashcards", "hands-on problems"]` — use this to choose content block type |
| llm_profile | jsonb | `{ notes, subject_confidence, learning_style_summary }` — pass directly into LLM system prompt |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### `roadmap_position` (table exists, empty)

Tracks where the student currently is in their roadmap. The roadmap itself is not stored — it is re-generated from Neo4j on each session start.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| student_id | uuid FK → students.id | |
| current_index | integer default 0 | Index into the topo-sorted concept list |
| updated_at | timestamptz | |

### `srs_records` (table exists, empty)

One row per (student, concept) pair. Created on first completion, updated on every review. Powers spaced repetition scheduling.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| student_id | uuid FK → students.id | |
| node_id | text | Matches `Concept.id` in Neo4j |
| ease_factor | float default 2.5 | SM-2 ease factor |
| interval_days | integer default 1 | |
| next_review_at | timestamptz | When to surface this concept for review |
| last_reviewed_at | timestamptz | |
| attempts | integer default 0 | |
| last_score | integer | 0–5 |

**Key query — get due reviews:**
```sql
SELECT node_id, next_review_at
FROM srs_records
WHERE student_id = $1 AND next_review_at <= NOW()
ORDER BY next_review_at ASC
```

**Upsert after scoring:**
```sql
INSERT INTO srs_records (student_id, node_id, ease_factor, interval_days, next_review_at, last_reviewed_at, attempts, last_score)
VALUES ($1, $2, $3, $4, NOW() + ($4 || ' days')::interval, NOW(), 1, $5)
ON CONFLICT (student_id, node_id) DO UPDATE
  SET ease_factor = EXCLUDED.ease_factor,
      interval_days = EXCLUDED.interval_days,
      next_review_at = EXCLUDED.next_review_at,
      last_reviewed_at = EXCLUDED.last_reviewed_at,
      attempts = srs_records.attempts + 1,
      last_score = EXCLUDED.last_score;
```

---

## Session State — In-Memory

```python
SESSION_STORE = {}

SESSION_STORE[session_id] = {
    "student": { ...full student row from Supabase... },
    "node_ids": ["concept-1", "concept-2", ...],  # topo sort result, generated fresh each session
    "node_id": "intro-to-loops",                  # active concept
    "mode": "new_lesson",                          # "new_lesson" | "review" | "retry"
    "chunks": [ {"index": 0, "text": "..."}, ... ],
    "messages": [                                  # APPEND ONLY — never reset
        {"role": "assistant", "content": "..."},
        {"role": "user", "content": "..."},
    ],
    "attempt_count": 0,
    "block_index": 0,
    "blocks_delivered": [],   # e.g. ["video", "flashcard"] — used to prevent regeneration
}
```

**Critical:** `messages` is append-only throughout the entire lesson — across content blocks AND knowledge check. Never reset it between phases. The full history is what gives the LLM memory.

---

## Backend — FastAPI Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/session/start` | Initialize session — generate roadmap from Neo4j, load student, check reviews |
| POST | `/lesson/block` | Generate next content block (MCQ, flashcard, video) |
| POST | `/lesson/message` | Handle student message during knowledge check |
| POST | `/lesson/complete` | Score, write SRS, advance roadmap |
| GET | `/student/{id}` | Fetch student profile |

---

## Pipeline — Step by Step

### Phase 1 — Session Start (`/session/start`)

**1.1** Receive `student_id`. Fetch full student row from Supabase.

**1.2** Query Neo4j and run topo sort to generate the ordered concept list if there does not exist something in the roadmap_cache table. Store as `node_ids` in session. Store in roadmap_cache if not already there.

**1.3** Read `roadmap_position` from Supabase. If no row exists, create one with `current_index = 0`.

**1.4** Query `srs_records` for due reviews (`next_review_at <= NOW()`).
- If reviews due → `active_node_id` = most overdue concept, `mode = review`
- If none due → `active_node_id = node_ids[current_index]`, `mode = new_lesson`

**1.5** Fetch chunks for `active_node_id` from Neo4j.

**1.6** Initialize session in `SESSION_STORE` with student, node_ids, node_id, mode, chunks, empty messages, attempt_count=0, block_index=0, blocks_delivered=[].

**1.7** Return `session_id` to frontend.

---

### Phase 2 — Content Generation Loop (`/lesson/block`)

This is the most critical and currently most broken part of the system. The issues are: conversation history not being passed, content not personalised to the student, and the LLM regenerating the same blocks. All fixes are in how the session state and system prompt are constructed.

#### How the loop works

For each concept, the LLM generates **2–3 content blocks** in sequence before moving to the knowledge check. `block_index` tracks which block is active. `blocks_delivered` tracks which types have already been generated to prevent repetition.

Block types are chosen based on the student's `preferred_formats`:
- block_index 0 → first item in `preferred_formats`
- block_index 1 → second item
- block_index 2 → third item (or `mcq` as default)
- block_index == BLOCKS_PER_CONCEPT → transition to knowledge check

#### The system prompt — rebuilt every call, four required parts

All four parts are required on every call. Missing any part is what causes the current bugs.

```
PART 1 — STUDENT IDENTITY
(fixes: generic content, wrong difficulty level)

You are tutoring a student with the following profile:
- Name: {student.name}
- Background: {student.llm_profile.learning_style_summary}
- Confidence level: {student.llm_profile.subject_confidence}
- Learning goals: {student.learning_goals.primary_focus}
- Additional notes: {student.llm_profile.notes}

Tailor your language, examples, and depth specifically to this student.
A "beginner" student needs simple language, relatable analogies, and step-by-step explanation.
A "comfortable" or "very_familiar" student can handle technical depth and precise terminology.
Do not re-introduce yourself. Do not re-explain things already covered in the conversation.


PART 2 — CONCEPT CONTEXT
(fixes: LLM hallucinating or going off-topic)

You are teaching the following concept: {concept.name}
Here is the source material for this concept:
---
{chunks joined as plaintext}
---
Stay grounded in this material. Do not invent facts not present above.
All questions and explanations must reference this specific material.


PART 3 — WHAT HAS ALREADY BEEN COVERED
(fixes: regenerating same content block)

You have already delivered the following content blocks for this concept:
{blocks_delivered formatted as bullet list e.g. "- A video introduction\n- A flashcard on key terms"}
If nothing has been delivered yet, write: "No content has been delivered yet."

Do NOT repeat or regenerate any of the above. Move forward.


PART 4 — CURRENT TASK
{block_type_specific_instructions — see below}
```

#### Block type instructions (PART 4)

**MCQ:**
```
Generate a multiple choice question testing understanding of {concept.name}.
Ground the question in the source material above — do not ask a generic question about the topic.
Format as JSON only, no other text:
{
  "question": "...",
  "options": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "correct": "A",
  "explanation": "why this is correct, with reference to the source material"
}
```

**Flashcard:**
```
Generate a flashcard for the most important term or idea in {concept.name} not yet covered above.
Format as JSON only, no other text:
{
  "front": "term or short question",
  "back": "definition or answer written for a {student.llm_profile.subject_confidence} student"
}
```

**Video:**
```
Suggest a YouTube search query for a video that would help a {student.llm_profile.subject_confidence}
student understand {concept.name}.
Format as JSON only, no other text:
{
  "search_query": "specific search string",
  "why": "one sentence explaining why this suits this specific student"
}
```

#### Passing conversation history — the most common bug

Every LLM call must pass the full `messages` array from session state.



After each call, append both the trigger and the response to session messages immediately:

```python
session["messages"].append({
    "role": "user",
    "content": f"Generate a {block_type} for this concept."
})
session["messages"].append({
    "role": "assistant",
    "content": response.content[0].text
})
session["blocks_delivered"].append(block_type)
session["block_index"] += 1
```

#### Block routing logic

```python
BLOCKS_PER_CONCEPT = 3

@app.post("/lesson/block")
def get_next_block(session_id: str):
    session = SESSION_STORE[session_id]

    if session["block_index"] >= BLOCKS_PER_CONCEPT:
        return {"action": "knowledge_check"}

    formats = session["student"]["preferred_formats"]
    block_type = formats[session["block_index"]] if session["block_index"] < len(formats) else "mcq"

    content = generate_block(session, block_type)

    return {
        "action": "render_block",
        "type": block_type,
        "content": content
    }
```

---

### Phase 3 — Knowledge Check Loop (`/lesson/message`)

After all content blocks are delivered, the frontend transitions to a free-form knowledge check. The same `messages` array from Phase 2 carries over — do not reset it.

**3.1 Opening question** — on the first call with an empty student message, the LLM generates an open question. Add to PART 4 of the system prompt:

```
All content blocks for this concept have been delivered.
Ask the student one open-ended question to check their understanding of {concept.name}.
The question must be specific to the source material — not a generic comprehension check.
Do not ask a multiple choice question. Ask something that requires them to explain in their own words.
Keep the question concise.
```

**3.2 Classify intent using `claude-haiku-4-5`** when the student replies:

```python
async def classify_intent(message: str, concept_name: str) -> str:
    response = anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=10,
        system="""Classify the student's message into exactly one of three categories:
- question: the student is asking for clarification or help understanding something
- attempt: the student is trying to answer a question or demonstrate their understanding
- done: the student is signalling they want to move on (e.g. "done", "got it", "I'm ready", "move on")

Reply with only the single word: question, attempt, or done. No punctuation, no explanation.""",
        messages=[{"role": "user", "content": f"Concept being taught: {concept_name}\n\nStudent message: {message}"}]
    )
    return response.content[0].text.strip().lower()
```

**3.3 Branch on intent:**

- `question` → LLM answers the clarifying question. Do not increment `attempt_count`. Add to PART 4:
```
The student has a question. Answer it clearly and concisely using the source material.
Do not re-explain the entire concept. Address only what they asked.
After answering, prompt them to continue with the knowledge check.
```

- `attempt` → LLM evaluates the attempt. Increment `attempt_count`. Add to PART 4:
```
The student has attempted to answer your question. Their response is in the conversation above.
Evaluate their understanding specifically against the source material.
Tell them clearly what they got right and what they missed or got wrong — be specific, not generic.
If they have shown sufficient understanding, confirm it and ask them to type "done" to move on.
If they have not, ask a targeted follow-up question to guide them toward the right understanding.
Do not repeat content already covered. Build on what they said.
```

- `done` → proceed to Phase 4.

**3.4** If `attempt_count >= 3` and still no mastery — respond with a suggestion to revisit a prerequisite. Do not advance.

---

### Phase 4 — Scoring and SRS (`/lesson/complete`)

**4.1** Score using `claude-haiku-4-5`:

```python
response = anthropic.messages.create(
    model="claude-haiku-4-5-20251001",
    system="""You are evaluating a student's understanding of a concept based on a tutoring conversation.
Read the full conversation and score the student's demonstrated understanding from 0 to 5:
0-2: Does not understand the concept
3: Basic understanding, some gaps remain
4: Solid understanding, minor gaps
5: Strong understanding, could explain it to someone else
Return JSON only, no other text: {"score": N}""",
    messages=session["messages"],
    max_tokens=20,
)
score = json.loads(response.content[0].text)["score"]
```

**4.2** Run SM-2 and upsert `srs_records`:

```python
def sm2(ease, interval, score):
    if score < 3:
        return ease, 1
    new_ease = max(1.3, ease + 0.1 - (5 - score) * 0.08 + (5 - score) * 0.02)
    new_interval = round(interval * new_ease) if interval > 1 else (1 if interval == 0 else 6)
    return new_ease, new_interval
```

**4.3** Branch:
- `score >= 3` → `advance_roadmap()`, clear session entry, return `{"action": "advance"}`
- `score < 3` → set `mode = retry`, reset `block_index = 0` and `blocks_delivered = []`, keep `messages` intact, return `{"action": "retry"}`

**4.4** `advance_roadmap()`:
- Increment `current_index` in `roadmap_position`
- If `current_index == len(node_ids)` → return `{"action": "complete"}`

---

## Decision Rules

| Condition | Action |
|-----------|--------|
| `due_reviews` non-empty at session start | Load most overdue node, `mode = review` |
| `block_index < BLOCKS_PER_CONCEPT` | Generate next content block |
| `block_index == BLOCKS_PER_CONCEPT` | Transition to knowledge check |
| `intent == question` | Answer question, do not increment `attempt_count` |
| `intent == attempt` | Evaluate attempt, increment `attempt_count` |
| `intent == done` | Score → SRS write-back |
| `score >= 3` | Advance roadmap, clear session |
| `score < 3` | Reset `block_index` and `blocks_delivered`, `mode = retry`, keep messages |
| `attempt_count >= 3` and `score < 3` | Surface prerequisite suggestion, do not advance |
| `current_index == len(node_ids)` | Roadmap complete |

---

## Common Bugs — Causes and Fixes

| Bug | Cause | Fix |
|-----|-------|-----|
| LLM has no memory, repeats itself | `messages` array reset or not passed to LLM | Always pass `session["messages"]`. Append every exchange immediately. Never reconstruct from scratch. |
| Content not personalised to student | Student profile missing from system prompt | Include all of `llm_profile` in PART 1. Add explicit instruction to tailor to `subject_confidence`. |
| LLM regenerates same content block | No record of what was already delivered | Include `blocks_delivered` in PART 3. Append block type immediately after generation. |
| LLM generates generic questions | Chunks not in system prompt or not enforced | Include chunks in PART 2 with instruction: "Stay grounded in this material. Do not invent facts." |
| Knowledge check disconnected from lesson | `messages` reset between phases | Same `messages` array used across both phases — never reset between content blocks and knowledge check. |
| Wrong difficulty level | `subject_confidence` not used in prompt | Explicitly reference `subject_confidence` in PART 1 with concrete instructions per level. |

---

## LLM Call Reference

| Function | Model | Max tokens | Notes |
|----------|-------|-----------|-------|
| `generate_content` | claude-sonnet-4-6 | 1024 | All 4 system prompt parts required. Pass full messages history. |
| `classify_intent` | claude-haiku-4-5 | 10 | Pass concept name + student message. Returns single word only. |
| `score_response` | claude-haiku-4-5 | 20 | Pass full messages history. Returns `{"score": N}` only. |

---
Environment variables are in backend/.env

