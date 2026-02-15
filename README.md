# KUB
# Что такое KUB?
KUB - это аббревиатура от kazhurkeUserBot - моего Userbot-а для Telegram.
Цель - создать простого юзербота который сможет поставить даже ребенок, сделать простую систему модулей и просто чтобы был юзербот.
# Как установить KUB?
Установка максимально проста - клонируйте данный репозиторий, создайте venv (или используйте micromamba) и установите telethon и cryptg и пользуйтесь!
# Подробный процесс установки:
Стоит прояснить, kUB тестировался под Arch-based дистрибутивы, не факт что micromamba доступен на Debian\Ubuntu-based дистрибутивах.

Шаг 1: клонируйте данный репозиторий при помощи git clone.

Шаг 2: установите micromamba (yay -S micromamba-bin)

Шаг 3: инициализируйте micromamba в текущем shell-е, в моем случае это fish, если у вас zsh или bash в таком случае используйте команду которую вам даст micromamba 
Мой случай: eval "$(micromamba shell hook --shell fish)"

Шаг 4: создайте окружение micromamba: micromamba create -n kub python=3.13.7

Шаг 5: выполните команду pip install telethon cryptg

Шаг 6: запустите бота при помощи команды python kazhurkeUserBot.py

Шаг 7: пользуйтесь!
