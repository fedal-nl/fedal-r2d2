"""
This modeule provides CRUD operations for the spanglish module, including creating,
reading, updating, and deleting records related to translations, language detection results, 
and any other relevant data models defined in `models.py`. 
These functions will interact with the database using SQLAlchemy sessions and will be called by 
the API endpoints defined in `routers.py` to perform the necessary operations based on client requests.
"""

# from src.spanglish import models
# from sqlalchemy.orm import Session
# from src.enums import CategoryEnum


# def add_vocabulary(db: Session, vocabulary: str, category: CategoryEnum) -> models.Vocabulary:
#     """Add a new vocabulary entry to the database."""
#     new_entry = models.Vocabulary(text=vocabulary, category=category)
#     db.add(new_entry)
#     db.commit()
#     db.refresh(new_entry)
#     return new_entry


# def get_vocabulary_by_id(db: Session, vocab_id: int) -> models.Vocabulary | None:
#     """Retrieve a vocabulary entry by its ID."""
#     return db.query(models.Vocabulary).filter(models.Vocabulary.id == vocab_id).first()


# def get_vocabulary_by_text(db: Session, text: str) -> models.Vocabulary | None:
#     """Retrieve a vocabulary entry by its text."""
#     return db.query(models.Vocabulary).filter(models.Vocabulary.text == text).first()


# def add_translation(db: Session, vocabulary_id: int, translation_text: str) -> models.Translation:
#     """Add a new translation for a given vocabulary entry."""
#     new_translation = models.Translation(vocabulary_id=vocabulary_id, translation=translation_text)
#     db.add(new_translation)
#     db.commit()
#     db.refresh(new_translation)
#     return new_translation


# def add_verb_conjugation(
#         db: Session,
#         vocabulary_id: int,
#         yo: str,
#         tu: str,
#         ella_el: str,
#         nosotros: str,
#         vosotros: str,
#         ellos_ellas: str) -> models.Verb:
#     """Add verb conjugations for a given vocabulary entry."""
#     new_verb = models.Verb(
#         vocabulary_id=vocabulary_id,
#         yo=yo,
#         tu=tu,
#         ella_el=ella_el,
#         nosotros=nosotros,
#         vosotros=vosotros,
#         ellos_ellas=ellos_ellas
#     )
#     db.add(new_verb)
#     db.commit()
#     db.refresh(new_verb)
#     return new_verb


# def get_vocabularies_by_category(db: Session, category: CategoryEnum) -> list[models.Vocabulary]:
#     """Retrieve all vocabulary entries with the category and translations for a given category."""
    
#     return db.query(models.Vocabulary).filter(models.Vocabulary.category == category).all()


# def add_quiz_answers(
#         db: Session,
#         vocabulary_id: int,
#         user_answer: str,
#         is_correct: bool,
#         quiz_session_id: int
#     ) -> models.QuizAttempt:
#     """Add quiz answers for a given vocabulary entry."""
#     new_quiz_answer = models.QuizAttempt(
#         vocabulary_id=vocabulary_id,
#         user_answer=user_answer,
#         is_correct=is_correct,
#         quiz_session_id=quiz_session_id
#     )
#     db.add(new_quiz_answer)
#     db.commit()
#     db.refresh(new_quiz_answer)
#     return new_quiz_answer


# def add_quiz_session(db: Session) -> models.QuizSession:
#     """Add a new quiz session. This will be used to group quiz attempts together."""
#     new_quiz_session = models.QuizSession()
#     db.add(new_quiz_session)
#     db.commit()
#     db.refresh(new_quiz_session)
#     return new_quiz_session


# def get_quiz_results_by_session(db: Session, quiz_session_id: int) -> list[models.QuizAttempt]:
#     """Retrieve all quiz attempts for a given quiz session."""
#     return db.query(models.QuizAttempt).filter(models.QuizAttempt.quiz_session_id == quiz_session_id).all()
