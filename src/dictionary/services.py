# """
# Responsable for the business logic of the spanglish module, including operations related to
# translations, language detection, and any other core functionalities that the module provides.
# This is where the main processing and decision-making happens based on the data received from 
# the API endpoints defined in `routers.py` and the database interactions defined in `models.py`.
# """

# from sqlalchemy.orm import Session
# from src.spanglish import models
# from src.enums import CategoryEnum
# import logging
# logger = logging.getLogger(__name__)

# class SpanglishService:
#     def __init__(self, db: Session):
#         self.db = db

#     def translate_vocabulary(self, vocabulary: str, category: CategoryEnum) -> str:
#         """Translate a given vocabulary based on its category."""
#         logger.info("Translating vocabulary: %s in category: %s", vocabulary, category)
#         vocab_entry = self.db.query(models.Vocabulary).filter(
#             models.Vocabulary.text == vocabulary,
#             models.Vocabulary.category == category
#         ).first()
        
#         if not vocab_entry:
#             logger.warning("Vocabulary not found: %s", vocabulary)
#             return "Translation not found"

#         translations = self.db.query(models.Translation).filter(
#             models.Translation.vocabulary_id == vocab_entry.id
#         ).all()

#         if not translations:
#             logger.warning("No translations found for vocabulary ID: %d", vocab_entry.id)
#             return "Translation not found"

#         translation_texts = [t.translation for t in translations]
#         logger.info("Found translations for vocabulary ID %d: %s", vocab_entry.id, translation_texts)
#         return ", ".join(translation_texts)
    
    