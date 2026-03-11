"""
OVERWATCH — FAISS Face Index
================================
Loads face embeddings from the database and builds a FAISS
index for fast nearest-neighbour similarity search.
"""

import logging
from typing import Optional

import faiss
import numpy as np

from app.database.database import SessionLocal
from app.database.models import FaceRow

logger = logging.getLogger(__name__)

# InsightFace buffalo_l produces 512-d embeddings
_EMBEDDING_DIM = 512

# L2 distance threshold — below this we consider it a match.
# Typical InsightFace L2 distances for the same person are < 1.0.
_MATCH_THRESHOLD = 1.2


class FaceIndex:
    """
    In-memory FAISS index built from watchlist embeddings stored
    in PostgreSQL.

    Call ``reload()`` after registering new faces so the index
    picks up the latest data.
    """

    def __init__(self) -> None:
        self.dimension: int = _EMBEDDING_DIM
        self.index: faiss.IndexFlatL2 = faiss.IndexFlatL2(self.dimension)
        self.names: list[str] = []
        self.face_ids: list[int] = []
        self.load_faces()

    def load_faces(self) -> None:
        """Load all watchlist faces from the database into the FAISS index."""
        db = SessionLocal()
        try:
            faces = db.query(FaceRow).all()
        finally:
            db.close()

        if not faces:
            logger.info("FaceIndex: no watchlist faces in database")
            return

        embeddings = []
        for face in faces:
            embeddings.append(face.embedding)
            self.names.append(face.name)
            self.face_ids.append(face.id)

        vectors = np.array(embeddings, dtype="float32")
        self.index.add(vectors)
        logger.info("FaceIndex: loaded %d faces", len(faces))

    def reload(self) -> None:
        """Rebuild the index from scratch (call after new enrolments)."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.names.clear()
        self.face_ids.clear()
        self.load_faces()

    def search(
        self,
        embedding: np.ndarray,
    ) -> tuple[str, float]:
        """
        Find the nearest watchlist face for the given embedding.

        Args:
            embedding: 512-d face embedding vector.

        Returns:
            (name, distance) — ``"Unknown"`` if the index is empty
            or the distance exceeds the match threshold.
        """
        if self.index.ntotal == 0:
            return "Unknown", 0.0

        query = np.array([embedding], dtype="float32")
        distances, indices = self.index.search(query, 1)

        idx = int(indices[0][0])
        distance = float(distances[0][0])

        if idx < len(self.names) and distance < _MATCH_THRESHOLD:
            return self.names[idx], distance

        return "Unknown", distance
