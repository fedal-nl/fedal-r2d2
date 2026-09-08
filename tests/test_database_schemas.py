from src.apps.spanglish import models
from src.auth import models as auth_models
from src.modules.ai import models as ai_models
from src.modules.email import models as email_models
from src.modules.forms import models as form_models


def test_spanglish_tables_use_spanglish_schema() -> None:
    spanglish_models = (
        models.Language,
        models.Vocabulary,
        models.QuizSession,
        models.QuizAttempt,
    )
    assert all(model.__table__.schema == "spanglish" for model in spanglish_models)


def test_ai_tables_use_dedicated_ai_schema() -> None:
    """Keep reusable AI persistence outside every application schema."""
    assert ai_models.AIAgent.__table__.schema == "ai"
    assert ai_models.AIUsage.__table__.schema == "ai"


def test_shared_tables_use_public_schema() -> None:
    shared_models = (
        auth_models.User,
        auth_models.SocialProvider,
        auth_models.RefreshSession,
        email_models.EmailLog,
        form_models.ZaansrechtForm,
        form_models.FormSubmissionLog,
    )
    assert all(model.__table__.schema == "public" for model in shared_models)


def test_cross_application_foreign_keys_are_schema_qualified() -> None:
    user_fk = next(iter(models.Language.__table__.c.user_id.foreign_keys))
    vocabulary_fk = next(
        iter(models.Translation.__table__.c.vocabulary_id.foreign_keys)
    )
    assert user_fk.target_fullname == "public.users.id"
    assert vocabulary_fk.target_fullname == "spanglish.vocabulary.id"
    ai_fk = next(iter(models.VocabularyExample.__table__.c.ai_agent_id.foreign_keys))
    assert ai_fk.target_fullname == "ai.ai_agents.id"
