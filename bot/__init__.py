"""
Пакет бота. Содержит всю логику Telegram-бота.
"""

from .main import main
from .keyboards import *
from .utils import *
from .reminders import *

__all__ = ['main']