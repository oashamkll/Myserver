#!/usr/bin/env python3
import os
import sys
import telebot
import ai_council

# Load environment variables from .env file if it exists
if os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip()

# Get token from environment
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    print("[!] ERROR: TELEGRAM_BOT_TOKEN is not set!")
    sys.exit(1)

bot = telebot.TeleBot(TOKEN)

# Safe reply function to avoid crashing when message to be replied is not found
def safe_reply(message, text, **kwargs):
    try:
        return bot.reply_to(message, text, **kwargs)
    except Exception:
        try:
            return bot.send_message(message.chat.id, text, **kwargs)
        except Exception as e:
            print(f"[!] Error sending message to chat {message.chat.id}: {e}")
            return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    help_text = (
        "🤖 **Привет! Я твой автономный ИИ-ассистент управления сервером.**\n\n"
        "Отправь мне любую задачу обычным текстом, и я задействую "
        "консилиум ИИ (Gemini + Llama + Mistral) для её безопасного выполнения!\n\n"
        "**Команды:**\n"
        "🔹 `/ai <задача>` — Выполнить задачу через ИИ консилиум\n"
        "🔹 `/cmd <команда>` — Выполнить прямую bash-команду на сервере\n"
        "🔹 `/status` — Проверить статус сервера и свободное место\n"
        "🔹 `/help` — Показать эту справку\n\n"
        "_Пример:_ `Установи nginx и запусти его` или `Проверь загрузку процессора`"
    )
    safe_reply(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def send_status(message):
    status_msg = safe_reply(message, "⏳ Получаю информацию о системе...")
    if not status_msg:
        return
    try:
        import subprocess
        df_output = subprocess.check_output("df -h / | tail -n 1", shell=True, text=True).strip()
        free_ram = subprocess.check_output("free -h | grep Mem | awk '{print $4 \" свободных из \" $2}'", shell=True, text=True).strip()
        uptime = subprocess.check_output("uptime -p", shell=True, text=True).strip()
        
        status_text = (
            "⚙️ **Статус сервера:**\n"
            f"🟢 **Uptime:** {uptime}\n"
            f"💾 **Диск (Корень /):** {df_output}\n"
            f"🧠 **Память (RAM):** {free_ram}\n"
        )
        bot.edit_message_text(status_text, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка при получении статуса: {str(e)}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=['cmd'])
def execute_direct_cmd(message):
    cmd_text = message.text[5:].strip()
    if not cmd_text:
        safe_reply(message, "❌ Пожалуйста, укажите команду. Пример: `/cmd ls -la`", parse_mode='Markdown')
        return
        
    status_msg = safe_reply(message, f"🏃‍♂️ Выполняю команду:\n`{cmd_text}`...", parse_mode='Markdown')
    if not status_msg:
        return
    try:
        output = ai_council.execute_bash(cmd_text)
        # Handle long output by splitting or truncating
        if len(output) > 3500:
            output = output[:3500] + "\n... [вывод слишком длинный, обрезан] ..."
        
        bot.edit_message_text(
            f"✅ **Результат выполнения:**\n\n```\n{output}\n```", 
            chat_id=status_msg.chat.id, 
            message_id=status_msg.message_id, 
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка исполнения: {str(e)}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)

@bot.message_handler(commands=['ai'])
def run_ai_task_cmd(message):
    goal = message.text[4:].strip()
    if not goal:
        safe_reply(message, "❌ Пожалуйста, укажите задачу для ИИ. Пример: `/ai установи htop`", parse_mode='Markdown')
        return
    process_ai_task(message, goal)

@bot.message_handler(func=lambda message: True)
def run_ai_task_default(message):
    # If it's a general text message, treat it as an AI goal
    goal = message.text.strip()
    process_ai_task(message, goal)

def process_ai_task(message, goal):
    status_msg = safe_reply(message, f"🧠 **Консилиум ИИ думает над вашей задачей:**\n_\"{goal}\"_\n\n⏳ Пожалуйста, подождите, это займет около 10-15 секунд...", parse_mode='Markdown')
    if not status_msg:
        return
    
    try:
        # Run the consensus task
        res = ai_council.run_consensus_task(goal)
        
        # Prepare parts
        plan_text = res.get('plan', 'Нет плана')
        critique_text = res.get('critique', 'Нет критических замечаний')
        cmd_text = res.get('command', 'Команда отсутствует')
        output_text = res.get('output', 'Нет вывода')
        
        # Format response
        response = (
            f"🎯 **Задача:** {goal}\n\n"
            f"📋 **План действий (Gemini):**\n{plan_text}\n\n"
            f"⚠️ **Анализ безопасности (Llama):**\n{critique_text}\n\n"
            f"💻 **Итоговая команда (Mistral):**\n`{cmd_text}`\n\n"
            f"📊 **Результат выполнения:**\n```\n{output_text}\n```"
        )
        
        # If too long, split into messages or truncate
        if len(response) > 4000:
            # Send in parts or truncate output
            if len(output_text) > 2000:
                output_text = output_text[:2000] + "\n... [вывод обрезан] ..."
            response = (
                f"🎯 **Задача:** {goal}\n\n"
                f"📋 **План действий:**\n{plan_text[:1000]}...\n\n"
                f"⚠️ **Безопасность:**\n{critique_text[:1000]}...\n\n"
                f"💻 **Команда:** `{cmd_text}`\n\n"
                f"📊 **Вывод:**\n```\n{output_text}\n```"
            )

        bot.edit_message_text(response, chat_id=status_msg.chat.id, message_id=status_msg.message_id, parse_mode='Markdown')
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка работы консилиума ИИ: {str(e)}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)

if __name__ == "__main__":
    print("[*] Telegram Bot запущен и ожидает сообщений...")
    bot.infinity_polling()
