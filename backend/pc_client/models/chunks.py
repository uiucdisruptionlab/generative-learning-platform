from dataclasses import dataclass

@dataclass
class ChunkMetadata:

    offering_id : str # same as namespace title; just here for debugging purposes 
    source_type : str # for filtering purposes i.e user could ask for something specifically mentioned in the slides 
    topic : str # for topic filtering to bias retrieval 
    text : str # passed into embeddings model
    chunk_number : int # to retrieve adjacent chunks for more context

    def validate_data(self):

        if not self.offering_id or not self.offering_id.strip():
            return ValueError("Offering ID Missing")

        if not self.source_type or not self.source_type.strip():
            return ValueError("Source Type Missing")

        if not self.topic or not self.topic.strip():
            return ValueError("Topic Missing")

        if not self.text or not self.text.strip():
            return ValueError("Text Missing")

        if not isinstance(self.chunk_number, int):
            raise ValueError("Chunk number must be an integer")

        if self.chunk_number <= 0:
            raise ValueError(f"Invalid Chunk Number: {self.chunk_number}")

        if self.source_type not in {"slides", "notes", "assignments", "textbook"}:
            raise ValueError(f"Invalid Source Type: {self.source_type}")

    def to_dict(self):
        self.validate_data()
        return self.__dict__



@dataclass
class CourseChunk:
    id : str # chunk id, i.e lec03_chunk_{chunk_number}
    values : list[float] # vector embeddings for chunk 
    metadata : ChunkMetadata # metadata object

    def validate_data(self):
        if not self.id or not self.id.strip():
            raise ValueError("Chunk ID missing")

        if not self.values:
            raise ValueError("Embedding values missing")

    def to_pinecone_record(self):

        self.validate_data()

        return (
            self.id, 
            self.values,
            self.metadata.to_dict()
        )


