"""
OVERWATCH — FAISS Face Index
================================
Loads face embeddings from the database and builds a FAISS
index for fast nearest-neighbour similarity search.

faiss-cpu is an OPTIONAL dependency. If it is not installed the
index silently degrades — searches always return ("Unknown", 0.0).
"""

import logging
from typing import Optional

import numpy as np

from app.database.database import SessionLocal
from app.database.models import FaceRow

logger = logging.getLogger(__name__)

# InsightFace buffalo_l produces 512-d embeddings
_EMBEDDING_DIM = 512

# L2 distance threshold — below this we consider it a match.
# Typical InsightFace L2 distances for the same person are < 1.0.
_MATCH_THRESHOLD = 1.2


def _try_import_faiss():
    """Return the faiss module or None if it is not installed."""
    try:
        import faiss  # type: ignore[import]
        return faiss
    except ImportError:
        logger.warning(
            "faiss-cpu is not installed — face-recognition search disabled. "
            "Run: pip install -r requirements-optional.txt"
        )
        return None


class FaceIndex:
    """
    In-memory FAISS index built from watchlist embeddings stored
    in the database.

    Call ``reload()`` after registering new faces so the index
    picks up the latest data.

    If faiss-cpu is not installed the index is a no-op stub.
    """

    def __init__(self) -> None:
        self._faiss = _try_import_faiss()
        self.dimension: int = _EMBEDDING_DIM
        self.index = (
            self._faiss.IndexFlatL2(self.dimension) if self._faiss else None
        )
        self.names: list[str] = []
        self.face_ids: list[int] = []
        self.load_faces()

    def load_faces(self) -> None:
        """Load all watchlist faces from the database into the FAISS index."""
        if self.index is None:
            return

        db = SessionLocal()
        try:
            faces = db.query(FaceRow).all()
        except Exception:
            logger.exception("FaceIndex: failed to query database")
            return
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
        if self._faiss is None or self.index is None:
            return
        self.index = self._faiss.IndexFlatL2(self.dimension)
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
            (name, distance) — ``"Unknown"`` if the index is empty,
            faiss is unavailable, or distance exceeds the match threshold.
        """
        if self.index is None or self.index.ntotal == 0:
            return "Unknown", 0.0

        query = np.array([embedding], dtype="float32")
        distances, indices = self.index.search(query, 1)

        idx = int(indices[0][0])
        distance = float(distances[0][0])

        if idx < len(self.names) and distance < _MATCH_THRESHOLD:
            return self.names[idx], distance

        return "Unknown", distance
