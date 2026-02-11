from enum import Enum


class RecommendationType(str, Enum):
    PART_SUGGESTION = "part_suggestion"
    DIAGNOSTIC = "diagnostic"
