from cacheing.redis_client import *

sid = "demo-session"
write_student(sid, {
    "id": "student-001",
    "name": "Najam",
    "llm_profile": {"tone": "encouraging", "verbosity": "concise"},
    "preferred_formats": ["video", "flashcard"],
    "learning_goals": {"target": "understand income statements", "timeline": "2 weeks"}
})
write_mode(sid, "new_lesson")
write_node_id(sid, "concept_revenue_basics")
write_chunks(sid, [
    {"index": 0, "text": "Revenue is income earned from normal business operations."},
    {"index": 1, "text": "Revenue is often referred to as the top line because it sits at the top of the income statement."}
])