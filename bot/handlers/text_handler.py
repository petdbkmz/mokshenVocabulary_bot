from telegram import Update
from telegram.ext import ContextTypes
from database.users import is_editor
from config import ADMIN_ID

from .study import handle_answer
from .support import handle_support_message, handle_admin_response_text
from .admin import (
    handle_add_word, handle_delete_word, handle_search,
    handle_edit_field, handle_user_stats, handle_clear_stats,
    handle_notification
)
from .thanks import edit_thanks_text
from .dictionary import dictionary_search
from .start import start

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых вводов"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # ===== ОБРАБОТКА /cancel =====
    if text.lower() == '/cancel':
        context.user_data.clear()
        await update.message.reply_text("❌ Операция отменена.\nЧтобы перезапустить бота, отправь /start")
        return
    
    # ===== ПРИОРИТЕТНЫЕ ОБРАБОТЧИКИ =====
    
    # Поддержка - сообщение от пользователя
    if context.user_data.get('awaiting_support_message'):
        await handle_support_message(update, context)
        return
    
    # Поддержка - ответ админа
    if context.user_data.get('replying_to') and user_id == ADMIN_ID:
        await handle_admin_response_text(update, context)
        return
    
    # Рассылка уведомлений
    if context.user_data.get('awaiting_notification'):
        await handle_notification(update, context)
        return
    
    # Удаление слова
    if context.user_data.get('awaiting_delete_word'):
        await handle_delete_word(update, context)
        return
    
    # Добавление слова
    if context.user_data.get('awaiting_add_word'):
        await handle_add_word(update, context)
        return
    
    # Редактирование карточки
    if context.user_data.get('awaiting_edit'):
        await handle_edit_field(update, context)
        return
    
    # Поиск слов (админский)
    if context.user_data.get('awaiting_search'):
        await handle_search(update, context)
        return
    
    # Статистика пользователя (админ)
    if context.user_data.get('awaiting_user_stats'):
        await handle_user_stats(update, context)
        return
    
    # Очистка статистики (админ)
    if context.user_data.get('awaiting_clear_stats'):
        await handle_clear_stats(update, context)
        return
    
    # Редактирование текста благодарности
    if context.user_data.get('awaiting_thanks_edit'):
        await edit_thanks_text(update, context)
        return
    
    # Поиск в словаре
    if context.user_data.get('awaiting_dict_search'):
        await dictionary_search(update, context)
        return
    
    # ===== ОТВЕТ НА КАРТОЧКУ =====
    await handle_answer(update, context)

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка загруженного Excel файла"""
    user_id = update.effective_user.id
    
    if not await is_editor(user_id):
        await update.message.reply_text("❌ У вас нет прав для импорта слов.")
        return
    
    document = update.message.document
    if not document.file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_text("❌ Пожалуйста, отправь файл в формате .xlsx или .xls")
        return
    
    file = await context.bot.get_file(document.file_id)
    file_path = f"temp_{user_id}_{document.file_name}"
    await file.download_to_drive(file_path)
    
    await update.message.reply_text("⏳ Импортирую слова из Excel...")
    
    try:
        from database.cards import import_words_from_excel
        count, errors = import_words_from_excel(file_path, user_id)
        
        if count > 0:
            message = f"✅ Успешно импортировано <b>{count}</b> слов!\n"
            if errors:
                message += f"\n⚠️ Ошибки ({len(errors)}):\n"
                message += "\n".join(errors[:5])
                if len(errors) > 5:
                    message += f"\n... и ещё {len(errors) - 5} ошибок"
            await update.message.reply_text(message, parse_mode='HTML')
        else:
            message = "❌ Не удалось импортировать слова.\n\nОшибки:\n"
            message += "\n".join(errors[:5])
            await update.message.reply_text(message)
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при импорте: {e}")
    
    try:
        import os
        os.remove(file_path)
    except:
        pass