# 🇷🇺Русский

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

Шаг 5: войдите в окружение micromamba activate kub

Шаг 6: выполните команду pip install telethon cryptg

Шаг 7: запустите бота при помощи команды python kazhurkeUserBot.py

Шаг 8: пользуйтесь!

## FAQ:

# Как устанавливать зависимости к модулям?
На данном этапе проекта установка зависимостей к модулям автоматическая, но если вы хотите поставить их руками, то это осуществляется следующим образом:

Инициализируйте micromamba в текущем shell-е (в моем случае это: eval "$(micromamba shell hook --shell fish)" )

Войдите в окружение в котором находится kUB (например: micromamba activate kub)

Напишите pip install *название зависимости*, благо kUB сам их говорит если установка прошла неудачно из-за отсутствия зависимостей

# Я хочу делать модули для kUB, это возможно?
Конечно! Весь userbot построен на модулях, если вы хотите создавать модули берите в руки документацию (https://github.com/KozhurYT/KUB/blob/main/Module-Documentation.md), расчехляйте свое IDE где вы пишете код и вперед!

# У меня еще остались вопросы.....
Просто напишите мне в Telegram! @kozhura_ubezhishe_player_fly

# 🇺🇸English
# KUB

## What is KUB?

KUB is an abbreviation for kazhurkeUserBot — my Userbot for Telegram. The goal is to create a simple userbot that even a child could set up, make a simple module system, and just to have a userbot.

## How to install KUB?

Installation is as simple as it gets — clone this repository, create a venv (or use micromamba), install telethon and cryptg, and you're good to go!

### Detailed installation process:

It's worth clarifying that kUB was tested on Arch-based distributions; there's no guarantee that micromamba is available on Debian/Ubuntu-based distributions.

**Step 1:** Clone this repository using git clone.

**Step 2:** Install micromamba (`yay -S micromamba-bin`)

**Step 3:** Initialize micromamba in your current shell. In my case it's fish; if you use zsh or bash, use the command that micromamba provides you. My case: `eval "$(micromamba shell hook --shell fish)"`

**Step 4:** Create a micromamba environment: `micromamba create -n kub python=3.13.7`

**Step 5:** Enter the environment: `micromamba activate kub`

**Step 6:** Run the command `pip install telethon cryptg`

**Step 7:** Start the bot using the command `python kazhurkeUserBot.py`

**Step 8:** Enjoy!

## FAQ:

### How to install module dependencies?

At this stage of the project, module dependency installation is automatic, but if you want to install them manually, here's how:

Initialize micromamba in your current shell (in my case: `eval "$(micromamba shell hook --shell fish)"`)

Enter the environment where kUB is located (for example: `micromamba activate kub`)

Type `pip install dependency_name` — fortunately, kUB itself tells you the missing dependencies if the installation failed due to their absence.

### I want to create modules for kUB, is that possible?

Of course! The entire userbot is built on modules. If you want to create modules, grab the documentation (https://github.com/KozhurYT/KUB/blob/main/Module-Documentation.md), fire up your IDE where you write code, and go for it!

### I still have questions.....

Just message me on Telegram! @kozhura_ubezhishe_player_fly
