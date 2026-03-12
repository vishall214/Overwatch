"""
OVERWATCH — Face Recognition Service
========================================
Detects faces using InsightFace, generates 512-d embeddings,
and queries the FAISS watchlist index for identity matches.

InsightFace is an OPTIONAL dependency. The import is deferred to
``load_model()`` so the service can be instantiated even when the
package is not installed (face recognition will simply be unavailable).
"""

import logging
from typing import TYPE_CHECKING, Optional

import numpy as np

from app.config import get_settings
from .face_index import FaceIndex

if TYPE_CHECKING:
    from insightface.app import FaceAnalysis  # only for type hints

logger = logging.getLogger(__name__)


class FaceService:
    """
    Wraps InsightFace detection/embedding and FAISS search.

    Attributes:
        _app: InsightFace analysis pipeline (None until loaded).
        index: FAISS watchlist index.
        _is_loaded: Whether the model has been prepared.
    """

    def __init__(self) -> None:
        self._app: Optional["FaceAnalysis"] = None
        self.index: FaceIndex = FaceIndex()
        self._is_loaded: bool = False

    def load_model(self) -> bool:
        """
        Load InsightFace models (downloads on first run).

        Returns:
            True if the model was loaded successfully.
        """
        try:
            from insightface.app import FaceAnalysis  # lazy import
            settings = get_settings()
            det_size = int(settings.face_detection_size)
            self._app = FaceAnalysis(name="buffalo_l")
            self._app.prepare(ctx_id=0, det_size=(det_size, det_size))
            self._is_loaded = True
            logger.info("FaceService: InsightFace model loaded (det_size=%d)", det_size)
            return True
        except ImportError:
            logger.error(
                "FaceService: insightface is not installed. "
                "Run: pip install -r requirements-optional.txt"
            )
            return False
        except Exception:
            logger.exception("FaceService: failed to load InsightFace")
            return False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded

    def recognize_faces(
        self,
        frame: np.ndarray,
    ) -> list[dict]:
        """
        Detect faces in *frame*, generate embeddings, and look up
        identities in the watchlist.

        Args:
            frame: BGR numpy array.

        Returns:
            List of dicts with keys ``bbox``, ``name``, ``confidence``.
            ``confidence`` is the L2 distance (lower = more similar).
        """
        if self._app is None:
            return []

        faces = self._app.get(frame)
        results = []
        for face in faces:
            embedding = face.embedding
            name, distance = self.index.search(embedding)
            results.append({
                "bbox": face.bbox.tolist(),
                "name": name,
                "confidence": round(float(distance), 4),
                "embedding": embedding,
            })
        return results

    def get_embedding(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Detect a single face and return its embedding.

        Used by the enrolment endpoint.

        Args:
            frame: BGR image expected to contain exactly one face.

        Returns:
            512-d embedding array, or None if no face detected.
        """
        if self._app is None:
            return None

        faces = self._app.get(frame)
        if not faces:
            return None
        return faces[0].embedding
