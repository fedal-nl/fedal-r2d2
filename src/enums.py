from enum import Enum


class EmailStatus(str, Enum):
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    QUEUED = "QUEUED"

class FormStatus(str, Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    VIEWED = "VIEWED"
    ARCHIVED = "ARCHIVED"


class CategoryEnum(str, Enum):
    NOUN = "Noun"
    VERB = "Verb"
    ADJECTIVE = "Adjective"
    DAY = "Days"
    MONTH = "Months"
    COLOR = "Colors"
    BODY_PART = "Body Parts"
    ANIMAL = "Animals"
    FAMILY = "Family"
    NUMBERS = "Numbers"
    TIME = "Time"
    DIRECTIONS = "Directions"
    GREETINGS = "Greetings"
    WEATHER = "Weather"
    SONGS = "Songs"
    FOOD = "Food"
    PROFESSIONS = "Professions"
    PHRASES = "Phrases"

class LanguageEnum(str, Enum):
    SPANISH = "Spanish"
    ENGLISH = "English"

class AIAgentEnum(str, Enum):
    OPENAI = "OpenAI"
    GOOGLE = "Google"
    ANTHROPIC = "Anthropic"
    MISTRAL = "Mistral"
    XAI = "XAI"
    LLAMA = "LLaMA"

class SocialMediaPlatformEnum(str, Enum):
    FACEBOOK = "Facebook"
    TWITTER = "Twitter"
    INSTAGRAM = "Instagram"
    LINKEDIN = "LinkedIn"
    TIKTOK = "TikTok"
    GOOGLE = "Google"
    MICROSOFT = "Microsoft"
    APPLE = "Apple"
    AMAZON = "Amazon"
    GITHUB = "GitHub"
    SPOTIFY = "Spotify"
    EMAIL = "Email"

class VocabularyTypeEnum(str, Enum):
    PHRASE = "Phrase"
    WORD = "Word"
    SENTENCE = "Sentence"
    LYRIC = "Lyric"
    