"""
Language enum for multilingual support
"""
from enum import Enum

class Language(str, Enum):
    """Supported languages for accident reports"""
    DE = "de"
    EN = "en"
    NL = "nl" 