import json
from supabase_local import get_supabase_client

client = get_supabase_client()

resp2 = client.table('roadmap_cache').select('student_id, roadmap').limit(2).execute()
print('=== roadmap_cache node_ids and concept id fields ===')
for row in (resp2.data or []):
    roadmap = row.get('roadmap')
    if isinstance(roadmap, str):
        roadmap = json.loads(roadmap)
    sid = row['student_id']
    node_ids = (roadmap or {}).get('node_ids') or []
    lessons = (roadmap or {}).get('lessons') or []
    print(f'\nstudent_id={sid}')
    print(f'  node_ids (first 5): {node_ids[:5]}')
    print(f'  node_ids total: {len(node_ids)}')
    # Show concept id fields inside lessons
    for lsn in lessons[:2]:
        cids = [c.get('id') for c in (lsn.get('concepts') or [])]
        print(f'  lesson_id={lsn.get("lesson_id")}  concept ids={cids}')
