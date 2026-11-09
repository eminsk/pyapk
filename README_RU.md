<div align="center">

# ⚡ pureapk / pyapk

### Pure Python движок для Android APK, мульти-стор упаковщик и инструментарий
**Zero dependencies (0 внешних зависимостей), парсинг через zero-copy memoryview, 100% пройденных тестов на CPython 3.8–3.16, Free-Threaded (No-GIL) и PyPy.**

[ 🇬🇧 English Documentation ](https://github.com/eminsk/pyapk#readme) | [ 🇷🇺 Документация на русском ](https://github.com/eminsk/pyapk/blob/main/README_RU.md)

[![Версия релиза](https://img.shields.io/github/v/release/eminsk/pyapk?logo=github&label=Release&color=0969da)](https://github.com/eminsk/pyapk/releases)
[![Версия PyPI](https://img.shields.io/pypi/v/pureapk?logo=pypi&logoColor=white&label=PyPI&color=0969da&v=1.0.1)](https://pypi.org/project/pureapk/)
[![Версия Conda](https://img.shields.io/conda/vn/m_n_nik/pureapk?logo=anaconda&logoColor=white&label=Conda&color=44A833)](https://anaconda.org/m_n_nik/pureapk)
[![Скачивания PyPI](https://img.shields.io/pypi/dm/pureapk.svg?style=flat&logo=pypi)](https://pypi.org/project/pureapk/)
[![Debian / Ubuntu PPA](https://img.shields.io/badge/Debian%20%2F%20Ubuntu-APT%20PPA-E95420.svg?style=flat)](https://eminsk.github.io/ppa/)
[![Версии Python](https://img.shields.io/badge/python-3.8_--_3.16-3776AB.svg?style=flat&logo=python&logoColor=white)](https://pypi.org/project/pureapk/)
[![Free-Threaded No-GIL](https://img.shields.io/badge/No--GIL-3.13t%20--%203.16t-brightgreen?style=flat)](https://peps.python.org/pep-0703/)
[![PyPy](https://img.shields.io/badge/PyPy-3.8_--_3.12-yellow.svg?style=flat&logo=pypy)](https://pypy.org/)
[![Ноль зависимостей](https://img.shields.io/badge/зависимости-0%20внешних-success.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Платформы](https://img.shields.io/badge/платформы-Apple_macOS_%7C_Linux_%7C_Windows-lightgrey.svg?style=flat)](https://github.com/eminsk/pyapk)
[![Тесты](https://img.shields.io/badge/тесты-70%20passed%20(100%25)-2ea44f.svg?style=flat&logo=pytest&logoColor=white)](https://github.com/eminsk/pyapk)
[![CI Матрица](https://github.com/eminsk/pyapk/actions/workflows/ci.yml/badge.svg)](https://github.com/eminsk/pyapk/actions/workflows/ci.yml)
[![GitHub Stars](https://img.shields.io/github/stars/eminsk/pyapk?style=flat&logo=github)](https://github.com/eminsk/pyapk/stargazers)
[![Лицензия: MIT](https://img.shields.io/badge/Лицензия-MIT-yellow.svg?style=flat)](https://opensource.org/licenses/MIT)
[![Поддержать (USDT)](https://img.shields.io/badge/Donate-USDT_(TRC20)-26A17B?style=flat&logo=tether&logoColor=white)](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P)

> ### 🤝 Сообщество, поддержка и обратная связь
> - 🐛 **Нашли ошибку или некорректный APK?** Пожалуйста, [откройте Issue](https://github.com/eminsk/pyapk/issues) — багрепорты рассматриваются и закрываются оперативно!
> - 💬 **Вопросы, идеи по мобильной сборке или сторам?** Загляните в [GitHub Discussions](https://github.com/eminsk/pyapk/discussions).
> - ⭐ **Полезна библиотека?** Поставьте звезду репозиторию на GitHub — это помогает другим Python-разработчикам узнать о проекте!
> - ☕ **Поддержать разработку (USDT TRC-20):** `TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P` ([Проверить на TronScan](https://tronscan.org/#/address/TDVbEdnpgNgoAhNcn1EwXxWHiR3RKLit5P))

[**Быстрый старт**](#-установка) • [**Совместимость**](#-универсальная-матрица-совместимости) • [**Python API**](#-использование-python-api) • [**Kivy и Pygame**](#-поддержка-kivy-и-pygame-без-лишней-обвязки) • [**Публикация в сторы**](#-подготовка-к-публикации-в-магазины-приложений) • [**Команды CLI**](#-консольная-утилита-cli)

</div>

---

## 🧩 Универсальная матрица совместимости

`pureapk` **не требует скомпилированных C-расширений** и работает исключительно на стандартной библиотеке Python. Протестирован в 54 независимых средах CI с результатом 100% пройденных тестов:

| Среда / Интерпретатор | Поддерживаемые версии | Режим исполнения | Статус в CI |
|:---|:---|:---|:---:|
| **CPython (Стандартный)** | 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16 (Alpha) | Стандартный байткод + GIL | ✅ 100% Успешно (27/27) |
| **CPython (Free-Threaded)** | 3.13t, 3.14t, 3.15t, 3.16t (Alpha) | Многопоточность No-GIL (PEP 703) | ✅ 100% Успешно (12/12) |
| **PyPy (JIT Ускорение)** | pypy3.8, pypy3.9, pypy3.10, pypy3.11, pypy3.12 | Tracing JIT рантайм | ✅ 100% Успешно (15/15) |
| **Операционные системы** | Windows (7, 8, 10, 11), Linux, macOS (Intel и Apple Silicon) | x86_64, ARM64 | ✅ 100% Успешно |

---

## 🚀 Ключевые преимущества

- 🛡️ **Ноль внешних зависимостей (Zero Dependencies)**: Построен исключительно на примитивах стандартной библиотеки (`struct`, `zipfile`, `hashlib`, `xml.etree`). Больше не нужны гигабайты Android SDK, NDK, Java Virtual Machine и Gradle на хост-машине.
- 🚫 **Без Java и Android Studio**: Никакой установки 15–20 ГБ SDK, NDK, OpenJDK и Gradle. Все операции с APK (бинарный AXML, DEX, 16KB-выравнивание и подпись) выполняются на 100% чистом Python за секунды.
- 🔧 **Доработка и моддинг готовых APK**: Извлечение любого существующего APK (`pureapk extract`), замена кода/ресурсов/манифеста, добавление wheels, автоматическая очистка старого `META-INF/`, перевыравнивание под Android 15 и переподпись (`pureapk pack --sign`).
- ⚡ **Zero-Copy и минимальная память**: Во всех ключевых классах строго используется `__slots__` (без оверхеда динамического словаря `__dict__`) и срезы `memoryview`.
- 🎯 **Функциональная архитектура без циклов и ветвлений**: Чистые паттерны функционального программирования, таблицы диспетчеризации словарей и потоки итераторов для предсказуемого и быстрого исполнения в горячих путях.
- 🧵 **Безопасность в Free-Threaded (No-GIL)**: Поддержка параллельного парсинга без блокировок и потокобезопасная ленивая инициализация свойств.
- 📱 **Встроенный тулчейн для Kivy, Pygame и GUI**: Генерация каркасов проектов, создание манифестов и прямая упаковка в APK с 4-байтным и 16-килобайтным (Android 15+) ZIP-выравниванием ресурсов и библиотек `.so` (Android тег `0xd935`).
- 🧩 **Поддержка Android Wheels и Cython**: Нативная распаковка предсобранных `.whl` пакетов с раскладкой `.so` по каталогам `lib/<abi>/` и встроенный генератор GitHub Actions CI для облачной компиляции C/Cython под Android NDK без засорения локальной системы.
- 🏬 **Публикация в маркетплейсы**: Встроенная сборка пакетов для Google Play (`.aab` Android App Bundle), Apple App Store (`.ipa` с `Info.plist`) и Microsoft Store (`.msix` с `AppxBlockMap.xml`).
- 🛠️ **Двойной CLI**: Доступны алиасы команд `pureapk` и `pyapk` как с человекопонятным, так и со структурированным выводом в `--json`.

---

## 📦 Установка

```bash
# Стандартная чистая установка через PyPI (ноль зависимостей, всего ~35 КБ)
pip install pureapk

# С предустановленными библиотеками для локального запуска (опционально)
pip install "pureapk[flet]"    # вместе с Flutter/Flet
pip install "pureapk[kivy]"    # вместе с Kivy
pip install "pureapk[pygame]"  # вместе с Pygame-CE
pip install "pureapk[toga]"    # вместе с BeeWare Toga
pip install "pureapk[all]"     # всё включено

# Либо установка обратно-совместимого алиаса
pip install pyapk

# С помощью менеджера uv
uv add pureapk
```

### Установка готового универсального колеса прямо из GitHub Releases
```bash
pip install https://github.com/eminsk/pyapk/releases/download/v1.0.1/pureapk-1.0.1-py3-none-any.whl
```

### Установка в Ubuntu / Debian через официальный репозиторий APT (PPA)
```bash
# Подключение репозитория eminsk PPA
curl -sS https://eminsk.github.io/ppa/setup.sh | sudo bash

# Установка пакета pureapk
sudo apt install python3-pureapk

# Либо установка готового пакета .deb напрямую
sudo dpkg -i python3-pureapk_1.0.1-1_all.deb
```

### Установка через Conda / Mamba / Pixi (Anaconda.org)
```bash
# Установка через conda из персонального канала
conda install -c m_n_nik pureapk

# Либо через mamba / pixi
mamba install -c m_n_nik pureapk
pixi add --channel m_n_nik pureapk
```

---

## 💻 Использование Python API

### 1. Базовый анализ и инспекция APK

```python
from pureapk import APK

with APK("path/to/application.apk") as apk:
    print("Имя пакета:    ", apk.package_name)
    print("Версия:        ", apk.version_name)
    print("Код версии:    ", apk.version_code)
    print("Min SDK:       ", apk.min_sdk_version)
    print("Target SDK:    ", apk.target_sdk_version)
    print("Разрешения:    ", apk.permissions)
    print("Активити:      ", apk.activities)
    print("Архитектуры:   ", apk.native_architectures)
```

### 2. Быстрое извлечение метаданных в одну строчку

```python
import pureapk

metadata = pureapk.inspect("application.apk")
print(metadata["package_name"], metadata["version_name"])
```

### 3. Анализ Multi-DEX и Dalvik байткода

```python
with APK("application.apk") as apk:
    dex = apk.dex
    print(f"Всего DEX файлов: {dex.dex_count}")
    print(f"Всего классов:    {dex.total_classes}")
    print(f"Всего методов:    {dex.total_methods}")
    print(f"Всего полей:      {dex.total_fields}")
    print(f"Всего строк:      {dex.total_strings}")
```

### 4. Проверка подписей и отпечатков сертификатов

```python
with APK("application.apk") as apk:
    sig = apk.signature
    print("Подписан:   ", sig.is_signed)
    print("Схемы:      ", sig.scheme_names)  # например, ('v1', 'v2', 'v3')

    for cert in sig.certificates:
        print("Файл:       ", cert.filename)
        print("SHA-256:    ", cert.sha256)
        print("SHA-1:      ", cert.sha1)
        print("MD5:        ", cert.md5)
```

### 5. Проверка выравнивания 16 КБ (Android 15 Ready) и zipalign

```python
from pureapk import APK
from pureapk.builder import zipalign

# Проверка соответствия Android 15
with APK("application.apk") as apk:
    print("Android 15 Ready (16KB):", apk.is_aligned_16k)
    align_info = apk.check_alignment()
    print("Выровнено:", align_info["is_aligned"])
    print("Библиотек .so:", align_info["aligned_so_files"], "/", align_info["total_so_files"])

# Выравнивание существующего APK на чистом Python (4B для файлов, 16KB для .so)
zipalign("unaligned.apk", "aligned.apk", so_alignment=16384, file_alignment=4)
```

### 6. Распаковка Android Wheels (.whl) в проект

```python
from pureapk.wheels import AndroidWheelHelper

# Инспекция состава wheel
info = AndroidWheelHelper.inspect_wheel("numpy-2.1.0-cp312-android_aarch64.whl")
print(f"Пакет: {info['distribution_name']} {info['version']}, ABI: {info['detected_abi']}")
print(f"Найдено .so библиотек: {info['native_libraries_count']}")

# Распаковка: .so направляются в lib/<abi>/, а Python-код — в проект
AndroidWheelHelper.unpack_wheel("numpy-2.1.0-cp312-android_aarch64.whl", target_dir="./my_app")
```

### 7. Генерация облачного CI для Cython и NDK

```python
from pureapk.ci import GitHubCythonWorkflowHelper

# Генерация готового .github/workflows/build-native.yml и шаблонов Cython
res = GitHubCythonWorkflowHelper.scaffold_project("./my_app", cython=True)
print("Создан CI воркфлоу:", res["workflow_path"])
```

### 8. Доработка, модификация и переподпись готовых APK (Modding & Patching)

`pureapk` позволяет разобрать готовый APK, внести изменения и собрать новую подписанную версию без Java и Android Studio:

```python
from pureapk import APK
from pureapk.builder import pack
from pureapk.wheels import AndroidWheelHelper

# 1. Распаковываем существующий APK в рабочую папку
with APK("my_app_v1.apk") as apk:
    apk.extract("./patched_app")

# 2. Добавляем новые скомпилированные библиотеки (.so) из Android Wheel
AndroidWheelHelper.unpack_wheel("cool_lib-android_aarch64.whl", target_dir="./patched_app")

# 3. Собираем новую готовую версию v2:
#    - автоматически очищает старый META-INF/ (удаляет старую подпись)
#    - выравнивает .so библиотеки по границе 16 КБ (Android 15)
#    - генерирует свежие v1 и v2 цифровые подписи
pack(
    source_dir="./patched_app",
    output_apk="my_app_v2.apk",
    sign=True,
    auto_axml=True,
    so_alignment=16384,
)
```

---

## 🎮 Поддерживаемые Python GUI и игровые фреймворки

`pureapk` предоставляет готовую шаблонизацию проектов, синтез манифестов и прямую упаковку для всех ключевых Python-фреймворков на **любой операционной системе** (включая Windows 7/10/11, macOS, Linux) без необходимости ставить Android Studio:

| Фреймворк | Назначение и архитектура | Вспомогательный класс | Поддерживаемые форматы |
| :--- | :--- | :--- | :--- |
| **Kivy** | Сенсорный интерфейс, мобильные бизнес-клиенты, дашборды | `KivyAppHelper` | Android APK, Google Play AAB, iOS IPA, Windows MSIX |
| **Pygame** | 2D аркады, физические симуляции, ретро-игры | `PygameAppHelper` | Android APK, Google Play AAB, iOS IPA, Windows MSIX |
| **Flet** | Современный UI на Flutter (Material 3 / Cupertino) | `FletAppHelper` | Android APK, Google Play AAB, iOS IPA, Windows MSIX |
| **BeeWare (Toga)** | Нативные системные виджеты ОС (`android.widget.*`, WinUI) | `TogaAppHelper` | Android APK, Google Play AAB, iOS IPA, Windows MSIX |
| **Ren'Py** | Визуальные новеллы, текстовые квесты и сюжетные игры | `RenPyAppHelper` | Android APK, Google Play AAB, Windows MSIX |
| **WebView Apps** | HTML5/CSS/Tailwind UI + локальный Python бэкенд | `WebViewAppHelper` | Android APK, Google Play AAB, iOS IPA, Windows MSIX |
| **PySide6 / PyQt** | Qt for Android и десктопные приложения | `PySideAppHelper` | Android APK, Google Play AAB, Windows MSIX |

```bash
# Инициализация структуры мобильных и десктопных проектов
pureapk init-kivy my_kivy_app --title "Моё Kivy Приложение"
pureapk init-pygame my_pygame_app --title "Space Shooter"
pureapk init-flet my_flet_app --title "Flet Mobile App"
pureapk init-toga my_toga_app --title "BeeWare Native App"
pureapk init-renpy my_novel --title "Интерактивная Новелла"
pureapk init-webview my_web_app --title "HTML5 Гибридное Приложение"
pureapk init-pyside my_qt_app --title "PySide6 Mobile App"

# Мгновенная упаковка в APK (для теста или релизный режим для сторов)
pureapk pack-kivy my_kivy_app -o app.apk --release
pureapk pack-pygame my_pygame_app -o shooter.apk --release
pureapk pack-flet my_flet_app -o flet.apk --release
pureapk pack-toga my_toga_app -o toga.apk --release
pureapk pack-renpy my_novel -o novel.apk --release
pureapk pack-webview my_web_app -o webview.apk --release
pureapk pack-pyside my_qt_app -o qtapp.apk --release
```

### 📦 Установка сторонних Python-зависимостей (`install-deps`)

Устанавливайте любые чистые Python-пакеты из PyPI прямо в папку проекта. `pureapk` автоматически скомпилирует их в байткод (`.pyc`) и упакует в `assets/private.tar`:

```bash
# Установка отдельных пакетов (requests, urllib3, certifi, pydantic и др.)
pureapk install-deps my_app requests certifi urllib3

# Или установка списка зависимостей из requirements.txt
pureapk install-deps my_app -r requirements.txt
```

---

## 🏬 Подготовка к публикации в магазины приложений

`pureapk` поддерживает подготовку пакетов для личных кабинетов разработчика:

### 1. Google Play Console (`.aab` и релизные ключи)
Google Play требует формат Android App Bundle (`.aab`) и подпись продакшн-ключом:
```bash
# Генерация профиля релизного ключа
pureapk generate-keystore -o release.keystore --alias production

# Сборка пакета Google Play Android App Bundle (.aab)
pureapk pack-aab my_app/ -o application.aab
```

### 2. Apple App Store (`.ipa` и `Info.plist`)
Генерация структуры и упаковка iOS-пакетов для Apple Transporter / App Store Connect:
```bash
# Создание проекта iOS с файлом Info.plist
pureapk init-ios ios_project --title "MyIOSApp" --bundle-id "com.company.iosapp"

# Сборка в архив Apple App Store .ipa
pureapk pack-ipa ios_project/ -o application.ipa --title "MyIOSApp"
```

### 3. Microsoft Windows Store (`.msix` и `AppxBlockMap.xml`)
Генерация `AppxManifest.xml`, хэширование 64 КБ блоков и упаковка MSIX:
```bash
# Создание проекта Windows Store
pureapk init-windows win_project --title "MyWinApp" --package "MyCompany.MyWinApp"

# Сборка в пакет Microsoft Store .msix с картой блоков
pureapk pack-msix win_project/ -o application.msix
```

### 4. Китайские магазины приложений и мульти-канальная сборка (Huawei, Xiaomi, OPPO, Vivo, Tencent, TapTap)
В Китае сервисы Google Play заблокированы. Приложения распространяются через магазины производителей устройств, где требуются классические релизные `.apk` (формат Google Play `.aab` не принимается), обязательная 64-битная архитектура (`arm64-v8a`) и канальные метки (多渠道打包):
```bash
# Сборка маркированных APK под каждый китайский маркет одной командой:
pureapk pack-kivy my_app/ -o my_app_huawei.apk --channel huawei --release
pureapk pack-kivy my_app/ -o my_app_xiaomi.apk --channel xiaomi --release
pureapk pack-kivy my_app/ -o my_app_oppo.apk --channel oppo --release
pureapk pack-kivy my_app/ -o my_app_vivo.apk --channel vivo --release
pureapk pack-kivy my_app/ -o my_app_tencent.apk --channel tencent --release
```
Ваш Python-код может мгновенно считывать канал прямо во время выполнения:
```python
from pathlib import Path

channel_file = Path("assets/channel.txt")
store_channel = channel_file.read_text().strip() if channel_file.exists() else "generic"
print(f"Запущено из магазина: {store_channel}")
```

---

## 🔑 Сертификаты и цифровая подпись: Полное руководство

Публикация в магазины и распространение на устройствах требует цифровой подписи. Ниже приведено пошаговое руководство для каждой платформы.

### 1. 🤖 Android (Google Play, RuStore, Huawei AppGallery)

- **Debug-ключ (для тестирования на телефоне)**:
  Используется по умолчанию для быстрой установки по проводу или через Wi-Fi (`adb install app.apk`).
- **Release-ключ (для сторов и пользователей)**:
  Магазины приложений отвергают debug-подписи. Для релиза создаётся надёжный RSA-2048/4096 ключ:
  ```bash
  # Создание ключа релизной подписи через pureapk:
  pureapk generate-keystore -o release.keystore --alias production --password my_secret_pass

  # Либо через стандартную утилиту keytool:
  keytool -genkey -v -keystore release.keystore -alias production -keyalg RSA -keysize 2048 -validity 10000
  ```
- **Проверка подписи в pureapk**:
  ```bash
  pureapk verify my_app.apk
  # Вывод всех схем подписи (v1, v2, v3, v4) и отпечатков SHA-256 / SHA-1:
  pureapk info my_app.apk --json
  ```
- **Google Play App Signing**: При загрузке `.aab` в Google Play Console вы подписываете бандл своим ключом загрузки (**Upload Key**), а Google автоматически подписывает готовые APK своим мастер-сертификатом.

---

### 2. 🍏 Apple App Store (iOS & macOS)

- **Что требуется**:
  1. Аккаунт **Apple Developer Program** ($99/год).
  2. **Distribution Certificate** (`.p12` сертификат распространения из кабинета Apple Developer).
  3. **Provisioning Profile** (`embedded.mobileprovision`), привязанный к вашему App ID (например, `com.company.myapp`).
- **Как это работает в pureapk**:
  1. Создаём структуру с корректным `Info.plist`:
     ```bash
     pureapk init-ios my_app --title "CoolApp" --bundle-id "com.company.coolapp"
     ```
  2. Помещаем `embedded.mobileprovision` в проект и собираем `.ipa`:
     ```bash
     pureapk pack-ipa my_app/ -o CoolApp.ipa --title "CoolApp"
     ```
  3. Подписание IPA:
     - **На macOS**: `codesign -s "Apple Distribution: Team Name (TEAM_ID)" --entitlements entitlements.plist Payload/CoolApp.app`
     - **На Windows/Linux** (без Mac): с помощью открытой кроссплатформенной утилиты `zsign`:
       ```bash
       zsign -k cert.p12 -p password -m embedded.mobileprovision -o Signed.ipa CoolApp.ipa
       ```
  4. Загрузка в App Store: через бесплатную программу **Apple Transporter** (доступна для Windows и macOS) прямо в **App Store Connect**.

---

### 3. 🪟 Windows (Microsoft Store & Sideloading)

- **Для публикации в официальный Microsoft Store**:
  - Вам **НЕ нужно** покупать дорогостоящий сертификат Code Signing!
  - При регистрации в **Microsoft Partner Center** ($19 разово) вам присваивается уникальный **Publisher ID** (вид: `CN=12345678-ABCD-EF01-...`).
  - Укажите этот ID при генерации манифеста:
    ```bash
    pureapk init-windows win_app --title "CoolApp" --package "MyCompany.CoolApp"
    pureapk pack-msix win_app/ -o CoolApp.msix
    ```
  - Загрузите `CoolApp.msix` в Partner Center. **Microsoft Store автоматически подпишет ваш пакет своим доверенным сертификатом Authenticode во время публикации.**
- **Для локальной установки вне магазина (Sideloading)**:
  - Создайте бесплатный сертификат разработчика в PowerShell:
    ```powershell
    $cert = New-SelfSignedCertificate -Type Custom -Subject "CN=MyCompany" -KeyUsage DigitalSignature -FriendlyName "PureApk Dev Cert" -CertStoreLocation "Cert:\CurrentUser\My"
    Export-PfxCertificate -Cert $cert -FilePath dev_cert.pfx -Password (ConvertTo-SecureString -String "1234" -Force -AsPlainText)
    ```
  - Подпишите пакет с помощью `SignTool`:
    ```powershell
    signtool sign /fd SHA256 /a /f dev_cert.pfx /p 1234 CoolApp.msix
    ```

---

## 🖥️ Консольная утилита (CLI)

Устанавливаются команды `pureapk` и `pyapk`.

```bash
# Сводная информация об APK
pureapk info application.apk
pureapk info application.apk --json

# Декодирование бинарного AndroidManifest.xml
pureapk manifest application.apk
pureapk manifest application.apk --json

# Список объявленных разрешений (Permissions)
pureapk permissions application.apk

# Анализ DEX-файлов и количества методов
pureapk dex application.apk

# Список файлов в архиве с контрольными суммами CRC32
pureapk files application.apk

# Проверка целостности и подписи
pureapk verify application.apk

# Распаковка содержимого APK
pureapk extract application.apk -o output_dir/

# Сборка директории в APK с выравниванием по 4 байта
pureapk pack src_directory/ -o output.apk

# Быстрый старт проектов и упаковка (Kivy, Pygame, Flet, Toga, Ren'Py, WebView)
pureapk init-flet my_app --title "Flet App"
pureapk pack-flet my_app/ -o flet.apk --release

pureapk init-toga my_app --title "Toga App"
pureapk pack-toga my_app/ -o toga.apk --release

pureapk init-renpy my_novel --title "Visual Novel"
pureapk pack-renpy my_novel/ -o novel.apk --release

pureapk init-webview my_web --title "WebView App"
pureapk pack-webview my_web/ -o web.apk --release

pureapk init-kivy my_kivy --title "Kivy App"
pureapk pack-kivy my_kivy/ -o kivy.apk --release

pureapk init-pygame my_game --title "Pygame App"
pureapk pack-pygame my_game/ -o game.apk --release

pureapk init-pyside my_qt --title "PySide App"
pureapk pack-pyside my_qt/ -o qt.apk --release

# Установка зависимостей прямо в папку приложения
pureapk install-deps my_app/ requests certifi urllib3
pureapk install-deps my_app/ -r requirements.txt

# Цифровая подпись APK схемами v1 (JAR) и v2 (APK Signing Block)
pureapk sign my_app.apk

# Компиляция текстового AndroidManifest.xml в бинарный AXML
pureapk compile-manifest AndroidManifest.xml -o AndroidManifest.axml

# Проверка и выравнивание по страницам 16 КБ (готовность к Android 15)
pureapk zipalign -c application.apk
pureapk zipalign application.apk -o aligned.apk

# Распаковка Android Wheels (.whl -> lib/<abi>/ + модули Python)
pureapk unpack-wheel package-android_24_arm64_v8a.whl my_app/

# Генерация облачного CI для Cython и Android NDK (сборка без засорения системы)
pureapk init-ci my_app/ --cython

# Полный цикл доработки и переподписи готового APK:
pureapk extract app_v1.apk ./workspace/
pureapk install-deps ./workspace/ requests
pureapk unpack-wheel numpy-android_aarch64.whl ./workspace/
pureapk pack ./workspace/ -o app_v2.apk --sign

# Подготовка к магазинам приложений (Google Play AAB, Apple IPA, Windows MSIX)
pureapk pack-aab project_dir/ -o app.aab
pureapk init-ios ios_app/ --title "MyIOSApp" --bundle-id "com.company.app"
pureapk pack-ipa ios_app/ -o app.ipa --title "MyIOSApp"
pureapk init-windows win_app/ --title "MyWinApp" --package "MyCompany.MyWinApp"
pureapk pack-msix win_app/ -o app.msix
pureapk generate-keystore -o release.keystore --alias production
```

---

## 🧪 Тестирование

Тестовый набор обеспечивает **100% прохождение тестов**:

```bash
# Запуск pytest через uv
uv run pytest tests/ -v

# Запуск с измерением покрытия кода
uv run pytest --cov=pureapk tests/
```

---

## 📄 Лицензия

MIT License — Copyright (c) 2026 eminsk.
