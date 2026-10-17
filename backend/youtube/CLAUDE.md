# YouTube Search

`search_videos` is best effort. With no `YOUTUBE_API_KEY`, or on any request failure, it returns an empty list instead of raising, and callers treat videos as optional. Keep it that way so a quota error never fails a lesson.
